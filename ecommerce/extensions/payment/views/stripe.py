

import logging
import waffle
from ecommerce.extensions.offer.constants import DYNAMIC_DISCOUNT_FLAG
from ecommerce.core.url_utils import get_lms_url
from edx_rest_api_client.client import EdxRestApiClient

from django.http import JsonResponse
from oscar.core.loading import get_class, get_model

from ecommerce.extensions.basket.utils import basket_add_organization_attribute
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin
from ecommerce.extensions.checkout.utils import get_receipt_page_url
from ecommerce.extensions.payment.forms import StripeSubmitForm
from ecommerce.extensions.payment.processors.stripe import Stripe
from ecommerce.extensions.payment.views import BasePaymentSubmitView
from ecommerce.extensions.checkout.signals import send_confirm_purchase_email

logger = logging.getLogger(__name__)

Applicator = get_class('offer.applicator', 'Applicator')
BillingAddress = get_model('order', 'BillingAddress')
Country = get_model('address', 'Country')
NoShippingRequired = get_class('shipping.methods', 'NoShippingRequired')
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')
Basket = get_model('basket', 'basket')
UserAddress = get_model('address', 'UserAddress')


class StripeSubmitView(EdxOrderPlacementMixin, BasePaymentSubmitView):
    """ Stripe payment handler.

    The payment form should POST here. This view will handle creating the charge at Stripe, creating an order,
    and redirecting the user to the receipt page.
    """
    form_class = StripeSubmitForm

    @property
    def payment_processor(self):
        return Stripe(self.request.site)

    def form_valid(self, form):
        form_data = form.cleaned_data
        #basket = form_data['basket']
        committed_basket = Basket.objects.filter(owner=self.request.user, status="Commited").last()
        committed_basket.strategy = self.request.strategy
        committed_basket.save()
        payment_method = form_data['payment_method']
        billing_address_id = form_data['address_id']
        order_number = committed_basket.order_number
        if waffle.flag_is_active(self.request, DYNAMIC_DISCOUNT_FLAG) and committed_basket.lines.count() == 1:
            discount_lms_url = get_lms_url('/api/discounts/')
            lms_discount_client = EdxRestApiClient(discount_lms_url,jwt=self.request.site.siteconfiguration.access_token)
            ck = committed_basket.lines.first().product.course_id
            user_id = committed_basket.owner.lms_user_id
            response = lms_discount_client.course(ck).get()
            self.request.GET = self.request.GET.copy()
            self.request.GET['discount_jwt'] = response.get('jwt')
            self.request.POST = self.request.POST.copy()
            self.request.POST['discount_jwt'] = response.get('jwt')
        Applicator().apply(committed_basket, self.request.user, self.request)
        basket_add_organization_attribute(committed_basket, self.request.POST)
        committed_basket.freeze()

        try:
            # billing_address = self.payment_processor.get_address_from_token(token)
            billing_address = self.payment_processor.get_address_from_user_address(billing_address_id)
            
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                'An error occurred while parsing the billing address for basket [%d]. No billing address will be '
                'stored for the resulting order [%s].',
                committed_basket.id,
                order_number)
            billing_address = None

        try:
            self.handle_payment(payment_method, billing_address_id, committed_basket)
        except Exception:  # pylint: disable=broad-except
            logger.exception('An error occurred while processing the Stripe payment for basket [%d].', committed_basket.id)
            return JsonResponse({}, status=400)

        # Remove paid items from last open baskets
        user_baskets = Basket.objects.filter(owner=self.request.user, status="Open")
        if user_baskets.exists():
            last_open_basket = user_baskets.last()
            del_lines = committed_basket.all_lines()
            open_lines = last_open_basket.all_lines()
        for line in del_lines:
            product = line.product
            filtered_lines = open_lines.filter(product_id=product.id)
            if filtered_lines.exists():
                filtered_lines.delete();
            last_open_basket.save()

        try:
            order = self.create_order(self.request, committed_basket, billing_address=billing_address)
            send_confirm_purchase_email(None, user=self.request.user, order=order)
        except Exception:  # pylint: disable=broad-except
            logger.exception('An error occurred while processing the Stripe payment for basket [%d].', committed_basket.id)
            return JsonResponse({}, status=400)

        self.handle_post_order(order)

        receipt_url = get_receipt_page_url(
            site_configuration=self.request.site.siteconfiguration,
            order_number=order_number,
            disable_back_button=True,
        )
        return JsonResponse({'url': receipt_url}, status=201)
