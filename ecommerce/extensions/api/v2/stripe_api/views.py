from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ecommerce.core.models import User
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin
from ecommerce.extensions.payment.processors.stripe import Stripe
import stripe
from django.conf import settings
from oscar.core.loading import get_model
import logging
from django.db import IntegrityError, transaction
from oscar.apps.partner.strategy import Selector
logger = logging.getLogger(__name__)
BillingAddress = get_model('order', 'BillingAddress')
Basket = get_model('basket', 'Basket')
Country = get_model('address', 'Country')
stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


class CustomStripeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        API: /stripe_api/profile/?email={email_address}
        This function is used to send the stripe customer_id saved in user context and if it doesn't exist create one and return.
        """
        user = request.user
        if 'customer_id' in user.tracking_context:
            return Response({'message':'', 'status': True, 'result':{'customer_id':user.tracking_context['customer_id']}, 'status_code':200})
        else:
            customer_id, token = self.create_customer_id(request)
            if customer_id and token:
                user.tracking_context['customer_id'] = customer_id
                user.tracking_context['token'] = token
                user.save()
                return Response({'message':'', 'status': False, 'result':{'customer_id':customer_id}, 'status_code':400})
            else:
                return  Response({'message':'customer_id not found, please provide a token to continue.', 'status': False, 'result':{}, 'status_code':400})

    def create_customer_id(self, request):
        """
        This function is used to create a customer in stripe and return its customer_id.
        """
        if 'token' in request.data:
            token = request.data['token']
            billing_address = self.get_address_from_token(token)
            address = {
            'city': billing_address.line4,
            'country': billing_address.country,
            'line1': billing_address.line1,
            'line2': billing_address.line2,
            'postal_code': billing_address.postcode,
            'state': billing_address.state
            }
            customer = stripe.Customer.create(
                source=token,
                email=request.user.email,
                address=address,
                name=request.user.full_name
            )
            return customer['id'], token
        else:
            return None, None

    def get_address_from_token(self,token):
        """ Retrieves the billing address associated with token.

        Returns:
            BillingAddress
        """
        data = stripe.Token.retrieve(token)['card']
        try:
            country = Country.objects.get(iso_3166_1_a2__iexact=data['address_country'])
        except:
            country = "SG"
        address = BillingAddress(
        first_name=data['name'],    # Stripe only has a single name field
        last_name='',
        line1=data['address_line1'] or '',
        line2=data.get('address_line2') or '',
        line4=data['address_city'],  # Oscar uses line4 for city
        postcode=data.get('address_zip') or '',
        state=data.get('address_state') or '',
        country=country
        )
        return address

class PaymentView(APIView, EdxOrderPlacementMixin):

    @property
    def payment_processor(self):
        return Stripe(self.request.site)

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        email = user.email
        customer_id = user.tracking_context['customer_id']
        customer = stripe.Customer.retrieve(customer_id)
        user_basket = Basket.objects.filter(owner=request.user, status="Commited").last()
        user_basket.strategy = Selector().strategy(user=self.request.user)
        if user_basket.status == "Commited":
            total_amount = int(user_basket.total_incl_tax)
            #total_amount = 100
            if total_amount > 0:
                token = user.tracking_context['token']
                try:
                    with transaction.atomic():
                        payment_response = self.handle_payment(token, user_basket)
                        order = self.create_order(self.request, user_basket, billing_address=self.get_address_obj_from_customer(customer))
                        self.handle_post_order(order)
                        response = {"total_amount": payment_response.total, "transaction_id": payment_response.transaction_id, \
                                    "currency": payment_response.currency, "last_4_digits_of_card": payment_response.card_number, \
                                    "card_type": payment_response.card_type}
                        # change the status of last saved basket to open
                        baskets = Basket.objects.filter(owner=user, status="Open")
                        if baskets.exists():
                            last_open_basket = baskets.last()
                            del_lines = user_basket.all_lines()
                            open_lines = last_open_basket.all_lines()
                            for line in del_lines:
                                product = line.product
                                filtered_lines = open_lines.filter(product_id=product.id)
                                if filtered_lines.exists():
                                    filtered_lines.delete();
                                last_open_basket.save()



                        return Response({"message":"Payment completed.", "status": True, "result": response, "status_code":200})
                except Exception as e:
                    msg = 'Attempts to handle payment for basket ' + str(user_basket.id) + ' failed.'
                    return Response({"message": msg, "status": False, "result":{}, "status_code":400})
            else:
                return Response({"message":"Total amount must be greater than 0.", "status": False, "result":{}, "status_code":400})
        else:
            return Response({"message":"No item found in cart.", "status": False, "result":{}, "status_code":400})

    def get_address_obj_from_customer(self, customer):
        """ Create a BillingAddress Object from customer's address

        Returns:
            BillingAddress
        """
        customer_address = customer['address']
        try:
            country = Country.objects.get(name=customer_address['country'])
        except:
            country = country = Country.objects.get(iso_3166_1_a2__iexact="SG")

        address = BillingAddress(
        first_name=customer['name'],
        line1=customer_address['line1'] or '',
        line2=customer_address['line2'] or '',
        postcode=customer_address['postal_code'] or '',
        state=customer_address['state'] or '',
        country=country
        )
        return address

class CheckoutBasketMobileView(APIView, EdxOrderPlacementMixin):

    @property
    def payment_processor(self):
        return Stripe(self.request.site)

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        email = user.email
        customer_id = user.tracking_context['customer_id']
        customer = stripe.Customer.retrieve(customer_id)
        user_basket = Basket.objects.filter(owner=request.user, status="Commited").last()
        user_basket.strategy = Selector().strategy(user=self.request.user)
        if user_basket.status == "Commited":
            total_amount = int(user_basket.total_incl_tax)
            if total_amount > 0:
                token = user.tracking_context['token']
                try:
                    with transaction.atomic():
                        payment_response = self.make_stripe_payment_for_mobile(token, user_basket)
                        response = {"total_amount": payment_response.total, "transaction_id": payment_response.transaction_id, \
                                    "currency": payment_response.currency, "client_secret": payment_response.client_secret}
                        # change the status of last saved basket to open
                        baskets = Basket.objects.filter(owner=user, status="Open")
                        if baskets.exists():
                            last_open_basket = baskets.last()
                            del_lines = user_basket.all_lines()
                            open_lines = last_open_basket.all_lines()
                            for line in del_lines:
                                product = line.product
                                filtered_lines = open_lines.filter(product_id=product.id)
                                if filtered_lines.exists():
                                    filtered_lines.delete();
                                last_open_basket.save()



                        return Response({"message":"Payment completed.", "status": True, "result": response, "status_code":200})
                except Exception as e:
                    msg = 'Attempts to handle payment for basket ' + str(user_basket.id) + ' failed.'
                    return Response({"message": msg, "status": False, "result":{}, "status_code":400})
            else:
                return Response({"message":"Total amount must be greater than 0.", "status": False, "result":{}, "status_code":400})
        else:
            return Response({"message":"No item found in cart.", "status": False, "result":{}, "status_code":400})


class TokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        if 'token' in user.tracking_context:
            return Response({'message':'', 'status': True, 'result':{'token':user.tracking_context['token']}, 'status_code':200})
        else:
            return Response({'message':'Token not found', 'status': False, 'result':{'token': None}, 'status_code':400})
