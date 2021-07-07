from ecommerce.extensions import voucher
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
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest
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
from ecommerce.extensions.basket.utils import apply_offers_on_basket, validate_voucher, apply_voucher_on_basket_and_check_discount
from ecommerce.extensions.api.serializers import BasketSerializer, OrderSerializer
from ecommerce.extensions.api.throttles import ServiceUserThrottle
from ecommerce.extensions.basket.exceptions import VoucherException, RedirectException
import sys, os
from ecommerce.extensions.offer.dynamic_conditional_offer import DynamicPercentageDiscountBenefit
from ecommerce.extensions.api.handlers import jwt_decode_handler

import urllib
from ecommerce.extensions.offer.utils import get_redirect_to_email_confirmation_if_required
from ecommerce.enterprise.utils  import get_enterprise_customer_from_voucher
from django.utils.translation import ugettext as _
from edx_rest_framework_extensions.auth.bearer.authentication import BearerAuthentication
from rest_framework import status

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



    """ Apply Voucher Mobile API Functions """

def _verify_basket_not_empty(request, code):
    username = request.user and request.user.username
    if request.basket.is_empty:
        logger.warning(
            '[Code Redemption Failure] User attempted to apply a code to an empty basket. '
            'User: %s, Basket: %s, Code: %s',
            username, request.basket.id, code
        )
        raise VoucherException()
    return True


def _verify_voucher_not_already_applied(request, code):
    username = request.user and request.user.username
    if request.basket.contains_voucher(code):
        logger.warning(
            '[Code Redemption Failure] User tried to apply a code that is already applied. '
            'User: %s, Basket: %s, Code: %s',
            username, request.basket.id, code
        )
        messages.error(
            request,
            _("You have already added coupon code '{code}' to your basket.").format(code=code),
        )
        raise VoucherException()
    return True


def _get_stock_record(request, code):
    # TODO: for multiline baskets, select the StockRecord for the product associated
    # specifically with the code that was submitted.
    basket_lines = request.basket.all_lines()
    return basket_lines[0].stockrecord


def _get_voucher(request, code):
    try:
        return Voucher._default_manager.get(code=code)  # pylint: disable=protected-access
    except Voucher.DoesNotExist:
        messages.error(request, _("Coupon code '{code}' does not exist.").format(code=code))
        raise VoucherException()


def _verify_email_confirmation(request, voucher, product):
    offer = voucher.best_offer
    redirect_response = get_redirect_to_email_confirmation_if_required(request, offer, product)
    if redirect_response:
        raise RedirectException(response=redirect_response)


def _verify_enterprise_needs(request, voucher, code, stock_record):
    if get_enterprise_customer_from_voucher(request.site, voucher) is not None:
        # The below lines only apply if the voucher that was entered is attached
        # to an EnterpriseCustomer. If that's the case, then rather than following
        # the standard redemption flow, we kick the user out to the `redeem` flow.
        # This flow will handle any additional information that needs to be gathered
        # due to the fact that the voucher is attached to an Enterprise Customer.
        params = urllib.parse.urlencode(
            OrderedDict([
                ('code', code),
                ('sku', stock_record.partner_sku),
                ('failure_url', request.build_absolute_uri(
                    '{path}?{params}'.format(
                        path=reverse('basket:summary'),
                        params=urllib.parse.urlencode(
                            {
                                CONSENT_FAILED_PARAM: code
                            }
                        )
                    )
                ))
            ])
        )
        redirect_response = HttpResponseRedirect(
            request.build_absolute_uri(
                '{path}?{params}'.format(
                    path=reverse('coupons:redeem'),
                    params=params
                )
            )
        )
        raise RedirectException(response=redirect_response)


def _validate_voucher(request, voucher):
    username = request.user and request.user.username
    is_valid, message = validate_voucher(voucher, request.user, request.basket, request.site)
    if not is_valid:
        logger.warning('[Code Redemption Failure] The voucher is not valid for this basket. '
                        'User: %s, Basket: %s, Code: %s, Message: %s',
                        username, request.basket.id, voucher.code, message)
        messages.error(request, message)
        request.basket.vouchers.remove(voucher)
        raise VoucherException()
    return True


def _apply_voucher(request, voucher):
    username = request.user and request.user.username
    valid, message = apply_voucher_on_basket_and_check_discount(voucher, request, request.basket)
    if not valid:
        logger.warning('[Code Redemption Failure] The voucher could not be applied to this basket. '
                        'User: %s, Basket: %s, Code: %s, Message: %s',
                        username, request.basket.id, voucher.code, message)
        messages.warning(request, message)
        request.basket.vouchers.remove(voucher)
        return False
    else:
        messages.info(request, message)
        return True


def verify_and_apply_voucher(request, code):
    request.basket = Basket.objects.filter(owner=request.user, status="Commited").last()
    request.basket.strategy = request.strategy
   
    _verify_basket_not_empty_message = "User attempted to apply a code to an empty basket."
    _verify_voucher_not_already_applied_message = "User tried to apply a code that is already applied."
    _get_voucher_message = "Coupon code does not exist."
    _validate_voucher_message = "The voucher is not valid for this basket."
    _apply_voucher_message = "The voucher could not be applied to this basket."

    voucher_applied = False
    try:
        if _verify_basket_not_empty(request, code):
            _verify_basket_not_empty_message = ""

        if _verify_voucher_not_already_applied(request, code):
            _verify_voucher_not_already_applied_message = ""

        stock_record = _get_stock_record(request, code)
        voucher = _get_voucher(request, code)
        if voucher:
            _get_voucher_message = ""
            benefit_type = voucher.offers.all()[0].benefit.type
            benefit_value = voucher.offers.all()[0].benefit.value
            if benefit_type == "Percentage":
                basket_total_discounts_string = "-" + str(round(benefit_value, 2)) + "%"
            else:
                basket_total_discounts_string = "-S$" + str(round(benefit_value, 2))

        _verify_email_confirmation(request, voucher, stock_record.product)
        _verify_enterprise_needs(request, voucher, code, stock_record)

        request.basket.clear_vouchers()
        if _validate_voucher(request, voucher):
            _validate_voucher_message = ""

        if _apply_voucher(request, voucher):
            _apply_voucher_message = ""
            voucher_applied = True

        gst_amount = request.basket.total_incl_tax - request.basket.total_excl_tax
        gst_amount = str(round(gst_amount,2))
        basket_total_excl_tax_excl_discounts_string = request.basket.total_excl_tax_excl_discounts
        basket_total_excl_tax_excl_discounts_string = str(round(basket_total_excl_tax_excl_discounts_string, 2))
        basket_total_incl_tax_string = request.basket.total_incl_tax
        basket_total_incl_tax_string = str(round(basket_total_incl_tax_string ,2))

        data = {}
        data["discount"] = basket_total_discounts_string
        data["subtotal"] = basket_total_excl_tax_excl_discounts_string
        data["gst"] = gst_amount
        data["total"] = basket_total_incl_tax_string

    except VoucherException:
        message = _verify_basket_not_empty_message or _verify_voucher_not_already_applied_message or _get_voucher_message or _get_voucher_message or _validate_voucher_message or _apply_voucher_message
        voucher_applied = False

        if not voucher_applied:
            data = {"message": message}


    return data


@api_view(('POST',))
def apply_voucher_mobile(request):
    code = request.data.get('voucher')
    code = code.strip()
    data = verify_and_apply_voucher(request, code)

    if "message" in data.keys():
        return Response({'status_code' : 400, 'message': data["message"]})
    else:
        return Response({'status_code' : 200, 'data': data})



