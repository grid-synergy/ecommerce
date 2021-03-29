

import json

from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from oscar.apps.dashboard.offers.views import OfferMetaDataView as CoreOfferMetaDataView
from oscar.apps.dashboard.offers.views import OfferRestrictionsView as CoreOfferRestrictionsView
from oscar.apps.dashboard.offers.views import OfferWizardStepView
from oscar.apps.dashboard.offers.views import OfferBenefitView
from oscar.apps.dashboard.offers.forms import BenefitForm as CoreBenefitForm
from oscar.apps.dashboard.offers.views import OfferDetailView as CoreOfferDetailView
from django.contrib.sites.models import Site
from oscar.apps.dashboard.offers.views import OfferDeleteView as CoreOfferDeleteView
from oscar.core.loading import get_model
from django.http import HttpResponseRedirect

ConditionalOffer = get_model('offer', 'ConditionalOffer')

import logging


class OfferMetaDataView(CoreOfferMetaDataView):

    def _store_form_kwargs(self, form):
        session_data = self.request.session.setdefault(self.wizard_name, {})

        # Adjust kwargs to save site_id rather than site which can't be serialized in the session
        form_data = form.cleaned_data.copy()
        site = form_data['site']
        form_data['site_id'] = site.id
        del form_data['site']
        form_kwargs = {'data': form_data}
        json_data = json.dumps(form_kwargs, cls=DjangoJSONEncoder)
        session_data[self._key()] = json_data
        self.request.session.save()

    def _fetch_form_kwargs(self, step_name=None):

        if not step_name:
            step_name = self.step_name
        session_data = self.request.session.setdefault(self.wizard_name, {})
        json_data = session_data.get(self._key(step_name), None)
        if json_data:
            form_kwargs = json.loads(json_data)
            form_kwargs['data']['site'] = Site.objects.get(pk=form_kwargs['data']['site_id'])
            del form_kwargs['data']['site_id']
            return form_kwargs

        return {}




class OfferRestrictionsView(CoreOfferRestrictionsView):

    def form_valid(self, form):
        offer = form.save(commit=False)

        # Make sure to save offer.site from the session_offer
        session_offer = self._fetch_session_offer()
        offer.partner = session_offer.site.siteconfiguration.partner
        return self.save_offer(offer)

    def save_offer(self, offer):
        response = super().save_offer(offer)
        if len(offer.condition.range.all_products()) == 1 and offer.benefit.type == 'Percentage':
            site = self.request.site
            product = offer.condition.range.all_products()[0]
            sku = product.stockrecords.first().partner_sku
            data = {'discount_percentage': float(offer.benefit.value)}
            commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
            update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)
        return response



class OfferDetailView(CoreOfferDetailView):

    def suspend(self):
        response = super().suspend()
        if self.offer.is_suspended:
            offer = self.offer
            if len(offer.condition.range.all_products()) == 1 and offer.benefit.type == 'Percentage':
                site = Site.objects.get_current()
                product = offer.condition.range.all_products()[0]
                sku = product.stockrecords.first().partner_sku
                data = {'discount_percentage': 0.00}
                commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
                update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)
                if update_discount_response['status_code'] == 200:
                    return response



    def unsuspend(self):
        response = super().unsuspend()
        if not self.offer.is_suspended:
            offer = self.offer
            if len(offer.condition.range.all_products()) == 1 and offer.benefit.type == 'Percentage':
                site = Site.objects.get_current()
                product = offer.condition.range.all_products()[0]
                sku = product.stockrecords.first().partner_sku
                data = {'discount_percentage': float(offer.benefit.value)}
                commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
                update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)
                if update_discount_response['status_code'] == 200:
                    return response



class OfferDeleteView(CoreOfferDeleteView):

 
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        offer = self.object
        offer_type = offer.benefit.type
        product = offer.condition.range.all_products()[0]
        sku = product.stockrecords.first().partner_sku
        delete_response = self.object.delete()
        
        if len(offer.condition.range.all_products()) == 1 and offer_type == 'Percentage':
            site = Site.objects.get_current()
            data = {'discount_percentage': 0.00}
            commerce_api_client = site.siteconfiguration.lhub_commerce_api_client
            update_discount_response  = commerce_api_client.update_discount(sku).post(data=data)
            if update_discount_response['status_code'] == 200:
               return HttpResponseRedirect(success_url)

        return HttpResponseRedirect(success_url)
