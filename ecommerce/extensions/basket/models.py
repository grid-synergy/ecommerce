

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from edx_django_utils.cache import DEFAULT_REQUEST_CACHE
from oscar.apps.basket.abstract_models import AbstractBasket, AbstractLine
from oscar.core.loading import get_class

from ecommerce.extensions.analytics.utils import track_segment_event, translate_basket_line_for_segment
from ecommerce.extensions.basket.constants import TEMPORARY_BASKET_CACHE_KEY
import logging
from decimal import Decimal as D
from oscar.core.utils import get_default_currency, round_half_up

OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')
Selector = get_class('partner.strategy', 'Selector')
from django.conf import settings



@python_2_unicode_compatible
class Line(AbstractLine):

    @property
    def line_price_incl_tax_incl_discounts(self):
        # We use whichever discount value is set.  If the discount value was
        # calculated against the tax-exclusive prices, then the line price
        # including tax
        if self.line_price_incl_tax is not None and self._discount_incl_tax:
            discount_tax = D((settings.LHUB_TAX_PERCENTAGE/100)) * self._discount_incl_tax
            
            return max(0, self.line_price_incl_tax - self._discount_incl_tax - discount_tax)
        elif self.line_price_excl_tax is not None and self._discount_excl_tax:
            return max(0, round_half_up((self.line_price_excl_tax - self._discount_excl_tax) / self._tax_ratio))

        return self.line_price_incl_tax


    @property
    def line_price_excl_tax_incl_discounts(self):
        if self._discount_excl_tax and self.line_price_excl_tax is not None:
            return max(0, self.line_price_excl_tax - self._discount_excl_tax)
        if self._discount_incl_tax and self.line_price_incl_tax is not None:
            # This is a tricky situation.  We know the discount as calculated
            # against tax inclusive prices but we need to guess how much of the
            # discount applies to tax-exclusive prices.  We do this by
            # assuming a linear tax and scaling down the original discount.
            return max(0, self.line_price_excl_tax - self._discount_incl_tax)
        return self.line_price_excl_tax


    @property
    def line_tax(self):
        if self.is_tax_known:
            return self.line_price_incl_tax_incl_discounts - self.line_price_excl_tax_incl_discounts



@python_2_unicode_compatible
class Basket(AbstractBasket):
    site = models.ForeignKey(
        'sites.Site', verbose_name=_("Site"), null=True, blank=True, default=None, on_delete=models.SET_NULL
    )
    OPEN, MERGED, SAVED, FROZEN, SUBMITTED, COMMITED = (
        "Open", "Merged", "Saved", "Frozen", "Submitted", "Commited")
    STATUS_CHOICES = (
        (OPEN, _("Open - currently active")),
        (MERGED, _("Merged - superceded by another basket")),
        (SAVED, _("Saved - for items to be purchased later")),
        (FROZEN, _("Frozen - the basket cannot be modified")),
        (SUBMITTED, _("Submitted - has been ordered at the checkout")),
        (COMMITED, _("Commited - has been commited")),
    )
    status = models.CharField(
        _("Status"), max_length=128, default=OPEN, choices=STATUS_CHOICES)


    def _get_total_discount(self, property):
        """
        For executing a named method on each line of the basket
        and returning the total.
        """
        total = D('0.00')
        for line in self.all_lines():
            try:
                total += getattr(line, property)
            except ObjectDoesNotExist:
                # Handle situation where the product may have been deleted
                pass
            except TypeError:
                # Handle Unavailable products with no known price
                info = self.get_stock_info(line.product, line.attributes.all())
                if info.availability.is_available_to_buy:
                    raise
                pass
        return total


    @property
    def total_discount(self):
        return self._get_total_discount('discount_value')


    @property
    def order_number(self):
        return OrderNumberGenerator().order_number(self)


    @classmethod
    def create_basket(cls, site, user):
        """ Create a new basket for the given site and user. """
        basket = cls.objects.create(site=site, owner=user)
        basket.strategy = Selector().strategy(user=user)
        return basket


    @classmethod
    def get_basket(cls, user, site):
        """ Retrieve the basket belonging to the indicated user.

        If no such basket exists, create a new one. If multiple such baskets exist,
        merge them into one.
        """
        editable_baskets = cls.objects.filter(site=site, owner=user, status__in=cls.editable_statuses)
        if not editable_baskets:
            basket = cls.create_basket(site, user)
        else:
            stale_baskets = list(editable_baskets)
            basket = stale_baskets.pop(0)
            for stale_basket in stale_baskets:
                # Don't add line quantities when merging baskets
                basket.merge(stale_basket, add_quantities=False)

        # Assign the appropriate strategy class to the basket
        basket.strategy = Selector().strategy(user=user)

        return basket


    def flush(self):
        """Remove all products in basket and fire Segment 'Product Removed' Analytic event for each"""
        cached_response = DEFAULT_REQUEST_CACHE.get_cached_response(TEMPORARY_BASKET_CACHE_KEY)
        if cached_response.is_found:
            # Do not track anything. This is a temporary basket calculation.
            return
        for line in self.all_lines():
            # Do not fire events for free items. The volume we see for edX.org leads to a dramatic increase in CPU
            # usage. Given that orders for free items are ignored, there is no need for these events.
            if line.stockrecord.price_excl_tax > 0:
                properties = translate_basket_line_for_segment(line)
                track_segment_event(self.site, self.owner, 'Product Removed', properties)

        # Call flush after we fetch all_lines() which is cleared during flush()
        super(Basket, self).flush()  # pylint: disable=bad-super-call


    def add_product(self, product, quantity=1, options=None):
        """
        Add the indicated product to basket.

        Performs AbstractBasket add_product method and fires Google Analytics 'Product Added' event.
        """
        line, created = super(Basket, self).add_product(product, quantity, options)  # pylint: disable=bad-super-call
        cached_response = DEFAULT_REQUEST_CACHE.get_cached_response(TEMPORARY_BASKET_CACHE_KEY)
        if cached_response.is_found:
            # Do not track anything. This is a temporary basket calculation.
            return line, created

        # Do not fire events for free items. The volume we see for edX.org leads to a dramatic increase in CPU
        # usage. Given that orders for free items are ignored, there is no need for these events.
        if line.stockrecord.price_excl_tax > 0:
            properties = translate_basket_line_for_segment(line)
            properties['cart_id'] = self.id
            track_segment_event(self.site, self.owner, 'Product Added', properties)
        return line, created


    def clear_vouchers(self):
        """Remove all vouchers applied to the basket."""
        for v in self.vouchers.all():
            self.vouchers.remove(v)


    def __str__(self):
        return _("{id} - {status} basket (owner: {owner}, lines: {num_lines})").format(
            id=self.id,
            status=self.status,
            owner=self.owner,
            num_lines=self.num_lines)


    def is_product_exists(self, product):
        product_line = self.lines.filter(product_id=product.id)
        if product_line:
            return True
        return False



class BasketAttributeType(models.Model):
    """
    Used to keep attribute types for BasketAttribute
    """
    name = models.CharField(_("Name"), max_length=128, unique=True)

    def __str__(self):
        return self.name



class BasketAttribute(models.Model):
    """
    Used to add fields to basket without modifying basket directly.  Fields
    can be added by defining new types.  Currently only supports text fields,
    but could be extended
    """
    basket = models.ForeignKey('basket.Basket', verbose_name=_("Basket"), on_delete=models.CASCADE)
    attribute_type = models.ForeignKey(
        'basket.BasketAttributeType', verbose_name=_("Attribute Type"), on_delete=models.CASCADE
    )
    value_text = models.TextField(_("Text Attribute"))

    class Meta:
        unique_together = ('basket', 'attribute_type')


# noinspection PyUnresolvedReferences
from oscar.apps.basket.models import *  # noqa isort:skip pylint: disable=wildcard-import,unused-wildcard-import,wrong-import-position,wrong-import-order,ungrouped-imports
