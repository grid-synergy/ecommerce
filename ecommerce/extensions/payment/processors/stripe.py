

#Added Stripe Payment Processor by clintonb · Pull Request #1147 · edx/ecommerce
#https://github.com




#Type a message
""" Stripe payment processing. """


import logging
import six
import stripe
from oscar.apps.payment.exceptions import GatewayError, TransactionDeclined
from oscar.core.loading import get_model
import json


from ecommerce.extensions.payment.constants import STRIPE_CARD_TYPE_MAP
from ecommerce.extensions.payment.processors import (
    ApplePayMixin,
    BaseClientSidePaymentProcessor,
    HandledProcessorResponse,
    HandledMobileProcessorResponse
)

logger = logging.getLogger(__name__)

BillingAddress = get_model('order', 'BillingAddress')
Country = get_model('address', 'Country')
PaymentEvent = get_model('order', 'PaymentEvent')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
UserAddress = get_model('address', 'UserAddress')


class Stripe(ApplePayMixin, BaseClientSidePaymentProcessor):
    NAME = 'stripe'
    template_name = 'payment/stripe.html'

    def __init__(self, site):
        """
        Constructs a new instance of the Stripe processor.

        Raises:
            KeyError: If no settings configured for this payment processor.
        """
        super(Stripe, self).__init__(site)
        configuration = self.configuration
        self.publishable_key = configuration['publishable_key']
        self.secret_key = configuration['secret_key']
        self.country = configuration['country']

        stripe.api_key = self.secret_key

    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=True, **kwargs):
        raise NotImplementedError('The Stripe payment processor does not support transaction parameters.')

    def _get_basket_amount(self, basket):
        return str((basket.total_incl_tax * 100).to_integral_value())  

    def handle_processor_response(self, payment_method_id, address_id, basket=None, forMobile=False):
        import stripe
        stripe.api_key = "sk_test_51IAvKdCWEv86Pz7X7tWqBhz0TtXbJCekvZ8rh6gLJ5Nyj21dF2IQQ79UidYFsASUM15568caRymjgvWX9g0nqeY000YqSswEFM"

        payment_method = payment_method_id
        order_number = basket.order_number
        currency = basket.currency
        basket_id = json.dumps(basket.id)
        billing_address_id = address_id
        # NOTE: In the future we may want to get/create a Customer. See https://stripe.com/docs/api#customers.
        tracking_context = basket.owner.tracking_context or {}

        customer_id = tracking_context.get('customer_id')
        billing_address = UserAddress.objects.get(id = billing_address_id)
        stripe.Customer.modify_source(
            customer_id,
            payment_method,
            address_city = billing_address.line4,
            address_country = billing_address.country,
            address_line1 = billing_address.line1,
            address_line2 = billing_address.line2,
            address_state = billing_address.state,
            address_zip = billing_address.postcode
        )

        if not forMobile:
            try:
                payment_intent = stripe.PaymentIntent.create(
                    amount=self._get_basket_amount(basket),
                    currency=currency,
                    customer=customer_id,
                    description=order_number,
                    metadata={'order_number': order_number, 'basket_id': basket_id},
                    payment_method=payment_method,
                    confirm=True
                )
                transaction_id = payment_intent.id


                # NOTE: Charge objects subclass the dict class so there is no need to do any data transformation
                # before storing the response in the database.
                self.record_processor_response(payment_intent, transaction_id=transaction_id, basket=basket)
                logger.info('Successfully created Stripe charge [%s] for basket [%d].', transaction_id, basket.id)
            except stripe.error.CardError as ex:
                base_message = "Stripe payment for basket [%d] declined with HTTP status [%d]"
                exception_format_string = "{}: %s".format(base_message)
                body = ex.json_body
                logger.exception(
                    exception_format_string,
                    basket.id,
                    ex.http_status,
                    body
                )
                self.record_processor_response(body, basket=basket)
                raise TransactionDeclined(base_message, basket.id, ex.http_status)

            total = basket.total_incl_tax

            card_number = payment_intent.charges.data[0]["payment_method_details"]["card"]["brand"]
            card_type = payment_intent.charges.data[0]["payment_method_details"]["card"]["last4"]

            return HandledProcessorResponse(
                transaction_id=transaction_id,
                total=total,
                currency=currency,
                card_number=card_number,
                card_type=card_type
            )

        else:

            payment_intent = stripe.PaymentIntent.create(
                amount=self._get_basket_amount(basket),
                currency=currency,
                customer=customer_id,
                description=order_number,
                metadata={'order_number': order_number, 'basket_id': basket_id}
            )

            client_secret = payment_intent.client_secret
            total = basket.total_incl_tax
            card_number = ""
            card_type = ""

            return HandledMobileProcessorResponse(
                transaction_id=payment_intent.id,
                total=total,
                currency=currency,
                client_secret=client_secret,
                card_number=card_number,
                card_type=card_type,
            )

    def issue_credit(self, order_number, basket, reference_number, amount, currency):
        try:
            refund = stripe.Refund.create(charge=reference_number)
        except:
            msg = 'An error occurred while attempting to issue a credit (via Stripe) for order [{}].'.format(
                order_number)
            logger.exception(msg)
            raise GatewayError(msg)

        transaction_id = refund.id

        # NOTE: Refund objects subclass dict so there is no need to do any data transformation
        # before storing the response in the database.
        self.record_processor_response(refund, transaction_id=transaction_id, basket=basket)

        return transaction_id

    def get_address_from_token(self, token):
        """ Retrieves the billing address associated with token.

        Returns:
            BillingAddress
        """
        data = stripe.Token.retrieve(token)['card']
        address = BillingAddress(
            first_name=data['name'],    # Stripe only has a single name field
            last_name='',
            line1=data['address_line1'],
            line2=data.get('address_line2') or '',
            line4=data['address_city'],  # Oscar uses line4 for city
            postcode=data.get('address_zip') or '',
            state=data.get('address_state') or '',
            country=Country.objects.get(iso_3166_1_a2__iexact=data['address_country'])
        )
        return address

    def get_address_from_user_address(self, billing_address_id):
        """ Retrieves the billing address associated with User Address for billing.

        Returns:
            BillingAddress
        """

        data = UserAddress.objects.get(id = billing_address_id)
        logging.info(data)
        try:
            country = Country.objects.get(iso_3166_1_a2__iexact=data.country)
        except:
            country = Country.objects.get(iso_3166_1_a2__iexact="SG")

        address = BillingAddress(
            first_name=data.name,     # Stripe only has a single name field
            last_name='',
            line1=data.line1 or '',
            line2=data.line2 or '',
            line4=data.line4,            # Oscar uses line4 for city
            postcode=data.postcode or '',
            state=data.state or '',
            country=country
        )
        return address
