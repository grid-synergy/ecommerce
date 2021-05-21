

import csv
from ecommerce.extensions import voucher
import logging
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, response
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.contrib.sites.models import Site

from oscar.apps.dashboard.vouchers.views import VoucherCreateView as CoreVoucherCreateView
from oscar.apps.dashboard.vouchers.views import VoucherUpdateView as CoreVoucherUpdateView
from oscar.apps.dashboard.vouchers.views import VoucherDeleteView as CoreVoucherDeleteView

from oscar.core.loading import get_class, get_model
from oscar.core.utils import slugify
from oscar.views import sort_queryset

VoucherForm = get_class('dashboard.vouchers.forms', 'VoucherForm')
VoucherSetForm = get_class('dashboard.vouchers.forms', 'VoucherSetForm')
VoucherSetSearchForm = get_class('dashboard.vouchers.forms', 'VoucherSetSearchForm')
VoucherSearchForm = get_class('dashboard.vouchers.forms', 'VoucherSearchForm')
Voucher = get_model('voucher', 'Voucher')
VoucherSet = get_model('voucher', 'VoucherSet')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Benefit = get_model('offer', 'Benefit')
Condition = get_model('offer', 'Condition')
OrderDiscount = get_model('order', 'OrderDiscount')
Range = get_model('offer', 'Range')



class VoucherCreateView(CoreVoucherCreateView):

    @transaction.atomic()
    def form_valid(self, form):
        response = super().form_valid(form)

        voucher_id = Voucher.objects.latest().id
        voucher_data = self.request._post.copy()

        data = {}
        data["name"] = voucher_data["name"]
        data["coupon_code"] = voucher_data["code"]
        data["incentive_type"] = voucher_data["benefit_type"]
        data["incentive_value"] = voucher_data["benefit_value"]
        data["usage"] = voucher_data["usage"]
        data["start_datetime"] = str(voucher_data["start_datetime"])
        data["end_datetime"] = str(voucher_data["end_datetime"])
        data["is_exclusive"] = True if voucher_data["exclusive"] else False
        data["associated_ecommerce_coupon_id"] = voucher_id

        data["courses_id"] = []
        range = Range.objects.filter(id=voucher_data["benefit_range"]).first()
        for product in range.all_products():
            data["courses_id"].append(product.course_id)

        site =  Site.objects.get_current()
        commerce_voucher_api_client = site.siteconfiguration.lhub_commerce_coupon_api_client
        add_discount_response  = commerce_voucher_api_client.add.post(data=data)

        return response



class VoucherUpdateView(CoreVoucherUpdateView):

    @transaction.atomic()
    def form_valid(self, form):
        response = super().form_valid(form)

        voucher_data = self.request._post.copy()

        data = {}
        data["name"] = voucher_data["name"]
        data["coupon_code"] = voucher_data["code"]
        data["incentive_type"] = voucher_data["benefit_type"]
        data["incentive_value"] = voucher_data["benefit_value"]
        data["usage"] = voucher_data["usage"]
        data["start_datetime"] = str(voucher_data["start_datetime"])
        data["end_datetime"] = str(voucher_data["end_datetime"])
        data["associated_ecommerce_coupon_id"] = self.voucher.id
        try:
            if voucher_data["exclusive"]:
                data["is_exclusive"] = True
        except:
            data["is_exclusive"] =  False

        data["courses_id"] = []
        range = Range.objects.filter(id=voucher_data["benefit_range"]).first()
        for product in range.all_products():
            data["courses_id"].append(product.course_id)

        site =  Site.objects.get_current()
        commerce_voucher_api_client = site.siteconfiguration.lhub_commerce_coupon_api_client
        add_discount_response  = commerce_voucher_api_client.add.post(data=data)


        return response



class VoucherDeleteView(CoreVoucherDeleteView):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        site =  Site.objects.get_current()
        commerce_voucher_api_client = site.siteconfiguration.lhub_commerce_coupon_api_client
        try:
            delete_discount_response  = commerce_voucher_api_client.delete(self.object.id).delete()
            if delete_discount_response:
                delete_response = self.object.delete()
        except:
            messages.error(self.request, _("Coupon Not Deleted!"))
            return HttpResponseRedirect(request.environ["PATH_INFO"])

        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)


