

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

        # if offer:
        #     data = {}
        #     data["associated_ecommerce_offer_id"] = offer.id
        #     data["start_datetime"] = str(offer.start_datetime)
        #     data["end_datetime"] = str(offer.end_datetime)
        #     data["priority"] = offer.priority
        #     data["incentive_type"] = response.type
        #     data["incentive_value"] = float(round(response.value, 2))
        #     data["condition_type"] = offer.condition.type
        #     data["condition_value"] = float(round(offer.condition.value, 2))
        #     data["is_exclusive"] = offer.exclusive
        #     data["courses_id"] = []
        #     for product in offer.condition.range.all_products():
        #         data["courses_id"].append(product.course_id)

        #     site =  Site.objects.get_current()
        #     commerce_offer_api_client = site.siteconfiguration.lhub_commerce_offer_api_client
        #     update_discount_response  = commerce_offer_api_client.add.post(data=data)

        # if offer and len(offer.condition.range.all_products()) == 1 and offer.benefit.type == 'Percentage':
        #     site =  Site.objects.get_current()
        #     product = offer.condition.range.all_products()[0]
        #     sku = product.stockrecords.first().partner_sku
        #     data = {'discount_percentage': float(response.value)}
        #     commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
        #     update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)

        return response

