from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ecommerce.core.models import User
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin
from ecommerce.extensions.payment.processors.stripe import Stripe
import stripe
import waffle
from django.conf import settings
from oscar.core.loading import get_model
import logging
from django.db import IntegrityError, transaction
from oscar.apps.partner.strategy import Selector
from oscar.core.loading import get_class
from ecommerce.extensions.offer.constants import DYNAMIC_DISCOUNT_FLAG
from ecommerce.core.url_utils import get_lms_url
from edx_rest_api_client.client import EdxRestApiClient
from ecommerce.extensions.api.handlers import jwt_decode_handler
from ecommerce.extensions.offer.dynamic_conditional_offer import DynamicPercentageDiscountBenefit
import json
from ecommerce.extensions.api.serializers import BasketSerializer
import requests
from ecommerce.extensions.checkout.signals import send_confirm_purchase_email

logger = logging.getLogger(__name__)
BillingAddress = get_model('order', 'BillingAddress')
Basket = get_model('basket', 'Basket')
Order = get_model('order', 'Order')
Country = get_model('address', 'Country')
stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']
Applicator = get_class('offer.applicator', 'Applicator')


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
            customer_id = self.create_customer_id(request)
            if customer_id:
                user.tracking_context['customer_id'] = customer_id
                user.save()
                return Response({'message':'', 'status': True, 'result':{'customer_id':customer_id}, 'status_code':200})
            else:
                return  Response({'message':'customer_id not found, please provide a token to continue.', 'status': False, 'result':{}, 'status_code':400})

    def create_customer_id(self, request):
        """
        This function is used to create a customer in stripe and return its customer_id.
        """
        customer = stripe.Customer.create(
            email=request.user.email,
            name=request.user.full_name
        )
        return customer['id']

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
        if user_basket:
            user_basket.strategy = Selector().strategy(user=self.request.user)
        else:
            return Response({"message":"No item found in cart.", "status": False, "result": {}, "status_code":400})
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

                        # send's payment confirmation mail to user
                        try:
                            order = order.objects.get(basket=basket)
                            user = order.user
                            send_confirm_purchase_email(None, user=request.user, order=order)
                        except:
                            pass

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
        if user_basket:
            user_basket.strategy = Selector().strategy(user=self.request.user)
        else:
            return Response({"message":"No item found in cart.", "status": False, "result": {}, "status_code":400})

        if waffle.flag_is_active(request, DYNAMIC_DISCOUNT_FLAG) and user_basket.lines.count() > 0:
            discount_lms_url = get_lms_url('/api/discounts/')
            lms_discount_client = EdxRestApiClient(discount_lms_url,jwt=request.site.siteconfiguration.access_token)
            ck = user_basket.lines.first().product.course_id
            user_id = user_basket.owner.lms_user_id
            response = lms_discount_client.course(ck).get()
            jwt = jwt_decode_handler(response.get('jwt'))
            if jwt['discount_applicable']:
                offers = Applicator().get_offers(user_basket, request.user, request)
                user_basket.strategy = request.strategy
                discount_benefit =  DynamicPercentageDiscountBenefit()
                percentage = jwt['discount_percent']
                discount_benefit.apply(user_basket,'dynamic_discount_condition',offers[0],discount_percent=percentage)
        Applicator().apply(user_basket, self.request.user, self.request)

        if user_basket.status == "Commited":
            total_amount = int(user_basket.total_incl_tax)
            if total_amount > 0:
                try:
                    with transaction.atomic():
                        payment_response = self.make_stripe_payment_for_mobile(None, user_basket)
                        response = {"total_amount": payment_response.total, "transaction_id": payment_response.transaction_id, \
                                    "currency": payment_response.currency, "client_secret": payment_response.client_secret}

                        # Freezing basket to prevent student from getting enrolled to possibily unpaid courses
                        user_basket.status = Basket.FROZEN
                        user_basket.save()

                        return Response({"message":"Payment completed.", "status": True, "result": response, "status_code":200})
                except Exception as e:
                    logger.exception(e)
                    msg = 'Attempts to handle payment for basket ' + str(user_basket.id) + ' failed.'
                    return Response({"message": msg, "status": False, "result":{}, "status_code":400})
            else:
                return Response({"message":"Total amount must be greater than 0.", "status": False, "result":{}, "status_code":400})
        else:
            return Response({"message":"No item found in cart.", "status": False, "result":{}, "status_code":400})


class ConfirmPaymentMobileView(APIView, EdxOrderPlacementMixin):

    @property
    def payment_processor(self):
        return Stripe(self.request.site)

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if 'id' not in request.data:
            return Response({"message":"Please provide payment intent id", "status": False, "result": {}, "status_code":400})
        intent_id = request.data['id']
        payment_intent = stripe.PaymentIntent.retrieve(id=intent_id)

        if payment_intent.status != 'succeeded':
            return Response({"message":"Please confirm payment first, through payment intent confirmation", "status": False, "result": {}, "status_code":400})

        # Load and fetch basket id from payment intent
        # This basket would be a paid and frozen basket, hence safe to be enrolled.
        basket_id = json.loads(payment_intent.metadata.basket_id)
        if not basket_id:
            return Response({"status": False, "message": "Basket not found", "status_code": 404})
        basket = Basket.objects.get(id=basket_id)
        basket.strategy = Selector().strategy(user=self.request.user)

        # Get billing details from payment intent (to be specific, from payment method)
        billing_details = payment_intent.charges.data[0].billing_details

        # Create order and enroll user
        order = self.create_order(self.request, basket, billing_address=self.get_address_from_payment_intent(billing_details))
        self.handle_post_order(order)

        # Following work is to generate the require response
        response = requests.get(url=settings.ECOMMERCE_URL_ROOT + '/api/v2/get-basket-detail/'+str(basket_id) + '/')
        checkout_response = json.loads(response.text)

        for product in checkout_response['products']:
            for item in product:
                if item['code'] == 'course_key': 
                    course_id = item['value'] 

            lms_url = get_lms_url('/api/commerce/v2/checkout/' + course_id)
            commerce_response  = requests.get(url=str(lms_url),headers={'Authorization' : 'JWT ' + str(request.site.siteconfiguration.access_token)})
            commerce_response = json.loads(commerce_response.text)
            if commerce_response['status_code'] == 200:
                price = commerce_response['result']['modes'][0]['price']
                sku = commerce_response['result']['modes'][0]['sku']
                discount_applicable = commerce_response['result']['discount_applicable']
                discounted_price = commerce_response['result']['discounted_price']
                media = commerce_response['result']['media']['image'] 
                category = commerce_response['result']['new_category']
                title = commerce_response['result']['name']
                organization = commerce_response['result']['organization']
                course_info = {'course_id' : course_id ,'media': media, 'category': category, 'title': title, 'price': price, 'discount_applicable': discount_applicable, \
                              'discounted_price': discounted_price, 'organization': organization, 'sku': sku, 'code': "course_details"}
                product.append(course_info)

        checkout_response['products'] = [i for j in checkout_response['products'] for i in j if not i['code'] in ['certificate_type', 'course_key', 'id_verification_required']]
        response = {"order_number": payment_intent.description, "total": payment_intent.amount, "products": checkout_response['products']}

        # change the status of last saved basket to open
        baskets = Basket.objects.filter(owner=self.request.user, status="Open")
        if baskets.exists():
            last_open_basket = baskets.last()
            del_lines = basket.all_lines()
            open_lines = last_open_basket.all_lines()
            for line in del_lines:
                product = line.product
                filtered_lines = open_lines.filter(product_id=product.id)
                if filtered_lines.exists():
                    filtered_lines.delete();
            last_open_basket.save()


        return Response({"message":"order completed successfully", "status": True, "result": response, "status_code":200})

    def get_address_from_payment_intent(self, billing_details):
        """ Create a BillingAddress Object from intent's address

        Returns:
            BillingAddress
        """
        billing_details_address = billing_details['address']
        try:
            country = Country.objects.get(name=billing_details_address['country'])
        except:
            country = country = Country.objects.get(iso_3166_1_a2__iexact="SG")

        address = BillingAddress(
        first_name=billing_details['name'] or '',
        line1=billing_details_address['line1'] or '',
        line2=billing_details_address['line2'] or '',
        postcode=billing_details_address['postal_code'] or '',
        state=billing_details_address['state'] or '',
        country=country
        )
        return address


class TokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        if 'token' in user.tracking_context:
            return Response({'message':'', 'status': True, 'result':{'token':user.tracking_context['token']}, 'status_code':200})
        else:
            return Response({'message':'Token not found', 'status': False, 'result':{'token': None}, 'status_code':400})
