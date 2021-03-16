from ecommerce.core.models import User
from rest_framework.response import Response
import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import stripe
from django.conf import settings
from oscar.core.loading import get_model
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import	 IsAuthenticated
import stripe
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
import logging
from django.http import Http404
from oscar.core.loading import get_class, get_model
from rest_framework import generics, status, viewsets

import requests
import json
import waffle
from ecommerce.extensions.offer.constants import DYNAMIC_DISCOUNT_FLAG
from ecommerce.core.url_utils import get_lms_url
from edx_rest_api_client.client import EdxRestApiClient
from oscar.apps.partner import strategy
from django.contrib.auth import get_user_model
from oscar.apps.basket.views import * 
from ecommerce.extensions.basket.utils import apply_offers_on_basket
from ecommerce.extensions.api.serializers import BasketSerializer
from ecommerce.extensions.api.throttles import ServiceUserThrottle

Applicator = get_class('offer.applicator', 'Applicator')
Basket = get_model('basket', 'Basket')
logger = logging.getLogger(__name__)
Order = get_model('order', 'Order')
OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')
Product = get_model('catalogue', 'Product')
Selector = get_class('partner.strategy', 'Selector')
User = get_user_model()
Voucher = get_model('voucher', 'Voucher')
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')
NoShippingRequired = get_class('shipping.methods', 'NoShippingRequired')
from ecommerce.extensions.offer.dynamic_conditional_offer import DynamicPercentageDiscountBenefit
from ecommerce.extensions.api.handlers import jwt_decode_handler





@api_view()
@authentication_classes((JwtAuthentication,))
@permission_classes([IsAuthenticated])
def get_ephemeral_key(request):

    """
    API: /stripe_api/profile/?email={email_address}
    This function is used to send the stripe customer_id saved in user context and if it doesn't exist create one and return.
    """
    try:
        stripe_customer_id = request.GET.get('stripe_customer_id')
        key = stripe.EphemeralKey.create(customer=stripe_customer_id,stripe_version='2020-08-27')
        response = {'message': '' , 'status': True, 'result':key, 'status_code':200}
        return Response(response)
    except Exception as e:
        logging.info(e)
        return Response(str(e))



class BasketViewSet(viewsets.ReadOnlyModelViewSet):
    """ View Set for Baskets"""
    #permission_classes = (IsAuthenticated,)
    serializer_class = BasketSerializer
    throttle_classes = (ServiceUserThrottle,)
    #authentication_classes = (BearerAuthentication,)

    def get_queryset(self):
        user = self.request.user
        # only accessible for staff
        #if not user.is_staff:
            #raise PermissionDenied
        return Basket.objects.filter(site=self.request.site)









@api_view(('GET',))
def get_basket_content(request):

    try:
        checkout_response = None
        basket = None
        if request.GET.get('id'):
            id = request.GET.get('id')
        else:
            if request.user.baskets.filter(status=Basket.OPEN).exists():
                id = request.user.baskets.filter(status=Basket.OPEN).first().id
            else:
                id = -1

        response = requests.get(url=settings.ECOMMERCE_URL_ROOT + '/api/v2/get-basket-detail/'+str(id) + '/')
        checkout_response = json.loads(response.text)
        if not request.user.baskets.filter(id=id).exists():
            return Response({"status": False, "message": "Basket not found", "status_code": 404})
        basket = request.user.baskets.get(id=id)
        basket.strategy = request.strategy
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
                course_info = {'media': media, 'category': category, 'title': title, 'price': price, 'discount_applicable': discount_applicable, \
                              'discounted_price': discounted_price, 'organization': organization, 'sku': sku, 'code': "course_details"}
                product.append(course_info)

        if waffle.flag_is_active(request, DYNAMIC_DISCOUNT_FLAG) and basket.lines.count() == 1:
            discount_lms_url = get_lms_url('/api/discounts/')
            lms_discount_client = EdxRestApiClient(discount_lms_url,jwt=request.site.siteconfiguration.access_token)
            ck = basket.lines.first().product.course_id
            user_id = basket.owner.lms_user_id
            response = lms_discount_client.course(ck).get()
            jwt = jwt_decode_handler(response.get('jwt'))
            if jwt['discount_applicable']:
                offers = Applicator().get_offers(basket, request.user, request)
                basket.strategy = request.strategy
                discount_benefit =  DynamicPercentageDiscountBenefit()
                percentage = jwt['discount_percent']
                discount_benefit.apply(basket,'dynamic_discount_condition',offers[0],discount_percent=percentage)
        checkout_response.update({'basket_total': basket.total_incl_tax, 'shipping_fee': 0.0, 'status': True, "status_code": 200})   

        return Response(checkout_response)
    except Exception as e:
        logging.info(e)
        return Response(str(e))



@api_view(('GET',))
def get_basket_content_mobile(request):

    try:
        checkout_response = None
        basket = None
        if request.GET.get('id'):
            id = request.GET.get('id')
        else:
            if request.user.baskets.filter(status=Basket.OPEN).exists():
                id = request.user.baskets.filter(status=Basket.OPEN).first().id
            else:
                id = -1

        response = requests.get(url=settings.ECOMMERCE_URL_ROOT + '/api/v2/get-basket-detail/'+str(id) + '/')
        checkout_response = json.loads(response.text)
        if not request.user.baskets.filter(id=id).exists():
            return Response({"status": False, "message": "Basket not found", "status_code": 404})
        basket = request.user.baskets.get(id=id)
        basket.strategy = request.strategy
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

        if waffle.flag_is_active(request, DYNAMIC_DISCOUNT_FLAG) and basket.lines.count() == 1:
            discount_lms_url = get_lms_url('/api/discounts/')
            lms_discount_client = EdxRestApiClient(discount_lms_url,jwt=request.site.siteconfiguration.access_token)
            ck = basket.lines.first().product.course_id
            user_id = basket.owner.lms_user_id
            response = lms_discount_client.course(ck).get()
            jwt = jwt_decode_handler(response.get('jwt'))
            if jwt['discount_applicable']:
                offers = Applicator().get_offers(basket, request.user, request)
                basket.strategy = request.strategy
                discount_benefit =  DynamicPercentageDiscountBenefit()
                percentage = jwt['discount_percent']
                discount_benefit.apply(basket,'dynamic_discount_condition',offers[0],discount_percent=percentage)
        
        checkout_response['products'] = [i for j in checkout_response['products'] for i in j if not i['code'] in ['certificate_type', 'course_key', 'id_verification_required']]
        checkout_response.update({'basket_total': basket.total_incl_tax, 'shipping_fee': 0.0, 'status': True, "status_code": 200})   
       
        return Response(checkout_response)
    except Exception as e:
        logging.info(e)
        return Response(str(e))

