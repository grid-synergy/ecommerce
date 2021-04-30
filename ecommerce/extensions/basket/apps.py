

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from oscar.apps.basket import apps
from oscar.core.loading import get_class


class BasketConfig(apps.BasketConfig):
    name = 'ecommerce.extensions.basket'

    # pylint: disable=attribute-defined-outside-init
    def ready(self):
        super().ready()
        self.basket_add_items_view = get_class('basket.views', 'BasketAddItemsView')
        self.summary_view = get_class('basket.views', 'BasketSummaryView')
        self.delete_card_view = get_class('basket.views', 'DeleteCardApiView')
        self.update_card_view = get_class('basket.views', 'UpdateCardApiView')
        self.add_card_view = get_class('basket.views', 'AddCardApiView')

        self.address_add_new_view = get_class('basket.views', 'AddressAddNewView')
        self.address_edit_view = get_class('basket.views', 'AddressEditView')
        self.address_delete_view = get_class('basket.views', 'AddressDeleteView')

    def get_urls(self):
        urls = [
            url(r'^$', login_required(self.summary_view.as_view()), name='summary'),
            url(r'^(?P<pm_id>\w+)/$', login_required(self.summary_view.as_view()), name='summary'),
            url(r'^add/(?P<pk>\d+)/$', self.add_view.as_view(), name='add'),
            url(r'^vouchers/add/$', self.add_voucher_view.as_view(), name='vouchers-add'),
            url(r'^vouchers/(?P<pk>\d+)/remove/$', self.remove_voucher_view.as_view(), name='vouchers-remove'),
            url(r'^saved/$', login_required(self.saved_view.as_view()), name='saved'),
            url(r'^add/$', self.basket_add_items_view.as_view(), name='basket-add'),
            url(r'^card-delete-source/', self.delete_card_view.as_view(), name='card-delete-source'),
            url(r'^card-update-source/', self.update_card_view.as_view(), name='card-update-source'),
            url(r'^card-add-source/', self.add_card_view.as_view(), name='card-add-source'),
            url(r'^address-add-new/', self.address_add_new_view.as_view(), name='address-add-new'),
            url(r'^address-edit/', self.address_edit_view.as_view(), name='address-edit'),
            url(r'^address-delete/', self.address_delete_view.as_view(), name='address-delete'),
        ]
        return self.post_process_urls(urls)
