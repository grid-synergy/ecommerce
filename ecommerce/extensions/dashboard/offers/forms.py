

from django.contrib.sites.models import Site
from django.forms import ModelChoiceField
from oscar.apps.dashboard.offers.forms import MetaDataForm as CoreMetaDataForm
from oscar.core.loading import get_model
from oscar.apps.dashboard.offers.forms import BenefitForm as CoreBenefitForm
from oscar.core.loading import get_model
ConditionalOffer = get_model('offer', 'ConditionalOffer')
from django.contrib.sites.models import Site

import logging

class MetaDataForm(CoreMetaDataForm):
    site = ModelChoiceField(queryset=Site.objects.all(), required=True)

    class Meta:
        model = get_model('offer', 'ConditionalOffer')
        fields = ('name', 'description', 'site')




class BenefitForm(CoreBenefitForm):

    def save(self, *args, **kwargs):
        response = super().save(*args, **kwargs)
        offer = None
        if ConditionalOffer.objects.filter(benefit=response.id).exists():
            offer = ConditionalOffer.objects.filter(benefit=response.id)[0]

        if offer:
            ecommerce_data = {}
            ecommerce_data["associated_ecommerce_offer_id"] = offer.id
            ecommerce_data["start_datetime"] = offer.start_datetime
            ecommerce_data["end_datetime"] = offer.end_datetime
            ecommerce_data["priority"] = offer.priority
            ecommerce_data["incentive_type"] = offer.benefit.type
            ecommerce_data["incentive_value"] = offer.benefit.value
            ecommerce_data["condition_type"] = offer.condition.type
            ecommerce_data["condition_value"] = offer.condition.value
            ecommerce_data["is_exclusive"] = offer.exclusive
            ecommerce_data["courses_sku"] = []
            for product in offer.condition.range.all_products():
                ecommerce_data["courses_sku"].append(product.stockrecords.first().partner_sku)

        # if offer and len(offer.condition.range.all_products()) == 1 and offer.benefit.type == 'Percentage':
        #     site =  Site.objects.get_current()
        #     product = offer.condition.range.all_products()[0]
        #     sku = product.stockrecords.first().partner_sku
        #     data = {'discount_percentage': float(response.value)}
        #     commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
        #     update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)

        return response

