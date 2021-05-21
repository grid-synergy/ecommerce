from ecommerce.core.models import User
from rest_framework.response import Response
import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import stripe
from django.conf import settings
from oscar.core.loading import get_model
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import   IsAuthenticated
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
from ecommerce.extensions.api.serializers import BasketSerializer, OrderSerializer
from ecommerce.extensions.api.throttles import ServiceUserThrottle

import sys, os

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
from edx_rest_framework_extensions.auth.bearer.authentication import BearerAuthentication




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

        if len(basket.all_lines()) > 0:
            offers = Applicator().get_site_offers()
            basket.strategy = request.strategy
            Applicator().apply_offers(basket, offers)
        
        tax = basket.total_incl_tax - basket.total_excl_tax
        if settings.LHUB_TAX_PERCENTAGE:
            tax_percent = settings.LHUB_TAX_PERCENTAGE
        else:
            tax_percent = 7

        
        checkout_response.update({'basket_total': basket.total_incl_tax, 'basket_total_excl_tax': basket.total_excl_tax, 'tax': tax,'tax_percent': tax_percent, 'shipping_fee': 0.0, 'status': True, "status_code": 200})   
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
            logging.info("mahad")
            logging.info(commerce_response)
            if commerce_response['status_code'] == 200:
                price= float(commerce_response['result']['modes'][0]['price'])
                price_string = str("%.2f" % commerce_response['result']['modes'][0]['price'])
                sku = commerce_response['result']['modes'][0]['sku']
                discount_applicable = commerce_response['result']['discount_applicable']
                discounted_price = float(commerce_response['result']['discounted_price'])
                logging.info(discounted_price)
                discounted_price_string = str("%.2f" % commerce_response['result']['discounted_price'])
                logging.info("---------------------")
                logging.info(discounted_price_string)
                media = commerce_response['result']['media']['image'] 
                category = commerce_response['result']['new_category']
                title = commerce_response['result']['name']
                organization = commerce_response['result']['organization']
                if commerce_response['result']['available_vouchers']:
                    voucher_applicable = True
                    #discount_type = commerce_response['result']['available_vouchers'].discount_type
                else:
                    voucher_applicable = False
                    discount_type = ""
                course_info = {'course_id' : course_id ,'media': media, 'category': category, 'title': title, 'price': price, 'discount_applicable': discount_applicable, \
                        'discounted_price': discounted_price, 'organization': organization, 'sku': sku, 'code': "course_details" ,'discounted_price_string':discounted_price_string,'price_string' : price_string, 'voucher_applicable' : voucher_applicable, 'available_vouchers': commerce_response['result']['available_vouchers']}
                product.append(course_info)
        if len(basket.all_lines()) > 0:
            offers = Applicator().get_site_offers()
            basket.strategy = request.strategy
            Applicator().apply_offers(basket, offers)
        gst_amount = basket.total_incl_tax - basket.total_excl_tax
        if settings.LHUB_TAX_PERCENTAGE:
            tax_percent = settings.LHUB_TAX_PERCENTAGE
        else:
            tax_percent = 7
        tax_percent = str(tax_percent) + "%"
        gst_amount = str(round(gst_amount,2))
        basket_total_excl_tax_string = basket.total_excl_tax 
        basket_total_excl_tax_string = str(round(basket_total_excl_tax_string, 2))
        basket_total_incl_tax_string = basket.total_incl_tax
        basket_total_incl_tax_string = str(round(basket_total_incl_tax_string ,2))
        checkout_response['products'] = [i for j in checkout_response['products'] for i in j if not i['code'] in ['certificate_type', 'course_key', 'id_verification_required']]
        checkout_response.update({'basket_total': basket_total_incl_tax_string, 'basket_subtotal': basket_total_excl_tax_string , 'gst_tax': tax_percent ,'gst_amount': gst_amount ,'shipping_fee': 0.0, 'status': True, "status_code": 200})
        return Response(checkout_response)
    except Exception as e:
        logging.info(e)
        return Response(str(e))




@api_view(('GET',))
#@authentication_classes((BearerAuthentication,))
@permission_classes([IsAuthenticated])
def get_course_discount_info(request, sku):
    if not Product.objects.filter(stockrecords__partner_sku=sku).exists():
        return Response({"status": False, "message": "Course not found", "status_code": 404})
    product = Product.objects.get(stockrecords__partner_sku=sku)
    product_price = product.stockrecords.first().price_excl_tax
    discount_info = {'status_code':200, 'discount_applicable': False, 'discounted_price': product_price, 'original_price': product_price, 'discount_percentage': 0.00}

    offers = Applicator().get_site_offers()
    for offer in offers:
        if offer.condition.range and offer.condition.range.contains_product(product):
            if offer.benefit.type == 'Percentage':
                discounted_price = round((product_price - (offer.benefit.value/100) * product_price ), 2)
                discount_info.update({'discounted_price': discounted_price, 'discount_applicable': True, 'discount_percentage' : offer.benefit.value })
            break

        else:
             pass

    return Response(discount_info)

