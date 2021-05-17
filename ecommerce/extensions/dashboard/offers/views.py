

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
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
import slumber
import logging

ConditionalOffer = get_model('offer', 'ConditionalOffer')



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
        session_offer.site = Site.objects.get_current()
        offer.partner = session_offer.site.siteconfiguration.partner
        return self.save_offer(offer)

    def save_offer(self, offer):
        response = super().save_offer(offer)

        if offer:
            data = {}
            data["associated_ecommerce_offer_id"] = offer.id
            data["start_datetime"] = str(offer.start_datetime)
            data["end_datetime"] = str(offer.end_datetime)
            data["priority"] = offer.priority
            data["incentive_type"] = offer.benefit.type
            data["incentive_value"] = float(round(offer.benefit.value, 2))
            data["condition_type"] = offer.condition.type
            data["condition_value"] = float(round(offer.condition.value, 2))
            data["is_exclusive"] = offer.exclusive
            data["is_suspended"] = offer.is_suspended
            data["courses_id"] = []
            for product in offer.condition.range.all_products():
                data["courses_id"].append(product.course_id)

            site =  Site.objects.get_current()
            commerce_offer_api_client = site.siteconfiguration.lhub_commerce_offer_api_client
            add_discount_response  = commerce_offer_api_client.add.post(data=data)

        return response



class OfferDetailView(CoreOfferDetailView):

    def suspend(self):
        response = super().suspend()
        if self.offer.is_suspended:
            offer = self.offer

        if offer:
            data = {}
            data["associated_ecommerce_offer_id"] = offer.id
            data["start_datetime"] = str(offer.start_datetime)
            data["end_datetime"] = str(offer.end_datetime)
            data["priority"] = offer.priority
            data["incentive_type"] = offer.benefit.type
            data["incentive_value"] = float(round(offer.benefit.value, 2))
            data["condition_type"] = offer.condition.type
            data["condition_value"] = float(round(offer.condition.value, 2))
            data["is_exclusive"] = offer.exclusive
            data["is_suspended"] = offer.is_suspended
            data["courses_id"] = []
            for product in offer.condition.range.all_products():
                data["courses_id"].append(product.course_id)

            site =  Site.objects.get_current()
            commerce_offer_api_client = site.siteconfiguration.lhub_commerce_offer_api_client
            update_discount_response  = commerce_offer_api_client.add.post(data=data)

        return response


    def unsuspend(self):
        response = super().unsuspend()
        if not self.offer.is_suspended:
            offer = self.offer

        if offer:
            data = {}
            data["associated_ecommerce_offer_id"] = offer.id
            data["start_datetime"] = str(offer.start_datetime)
            data["end_datetime"] = str(offer.end_datetime)
            data["priority"] = offer.priority
            data["incentive_type"] = offer.benefit.type
            data["incentive_value"] = float(round(offer.benefit.value, 2))
            data["condition_type"] = offer.condition.type
            data["condition_value"] = float(round(offer.condition.value, 2))
            data["is_exclusive"] = offer.exclusive
            data["is_suspended"] = offer.is_suspended
            data["courses_id"] = []
            for product in offer.condition.range.all_products():
                data["courses_id"].append(product.course_id)

            site =  Site.objects.get_current()
            commerce_offer_api_client = site.siteconfiguration.lhub_commerce_offer_api_client
            update_discount_response  = commerce_offer_api_client.add.post(data=data)

        return response



class OfferDeleteView(CoreOfferDeleteView):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        offer = self.object
        offer_type = offer.benefit.type
        product = offer.condition.range.all_products()[0]
        sku = product.stockrecords.first().partner_sku

        if offer:
            site =  Site.objects.get_current()
            commerce_offer_api_client = site.siteconfiguration.lhub_commerce_offer_api_client
            try:
                delete_discount_response  = commerce_offer_api_client.delete(offer.id).delete()
                if delete_discount_response:
                    delete_response = self.object.delete()
            except slumber.exceptions.HttpNotFoundError:
                messages.error(self.request, _("Offer Not Deleted!"))
                return HttpResponseRedirect(request.environ["PATH_INFO"])
            except:
                messages.error(self.request, _("Offer Not Deleted!"))
                return HttpResponseRedirect(request.environ["PATH_INFO"])
        

        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)
