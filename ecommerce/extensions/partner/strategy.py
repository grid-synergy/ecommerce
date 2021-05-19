# from future import absolute_import

from django.utils import timezone
from oscar.apps.partner import availability, strategy
from oscar.core.loading import get_model

from ecommerce.core.constants import SEAT_PRODUCT_CLASS_NAME
from decimal import Decimal as D
import logging
from django.conf import settings
from collections import namedtuple

PurchaseInfo = namedtuple(
    'PurchaseInfo', ['price', 'availability', 'stockrecord'])

class CourseSeatAvailabilityPolicyMixin(strategy.StockRequired):
    """
    Availability policy for Course seats.

    Child seats are only available if the current date is not beyond the seat's enrollment close date.
    Parent seats are never available.
    """

    @property
    def seat_class(self):
        ProductClass = get_model('catalogue', 'ProductClass')
        return ProductClass.objects.get(name=SEAT_PRODUCT_CLASS_NAME)

    def availability_policy(self, product, stockrecord):
        """ A product is unavailable for non-admin users if the current date is
        beyond the product's expiration date. Products are always available for admin users.
        """

        is_staff = getattr(self.user, 'is_staff', False)
        is_available = product.expires is None or (product.expires >= timezone.now())
        if is_staff or is_available:
            return super(CourseSeatAvailabilityPolicyMixin, self).availability_policy(product, stockrecord)

        return availability.Unavailable()


class DefaultStrategy1(strategy.UseFirstStockRecord, CourseSeatAvailabilityPolicyMixin,
strategy.NoTax, strategy.Structured):
    """ Default Strategy """



class FixedRateTax(strategy.FixedRateTax):
    rate = D(settings.LHUB_TAX_PERCENTAGE/100)


    def get_rate(self, product, stockrecord):
        return self.rate



class Structured(strategy.Structured):

    def fetch_for_product(self, product, stockrecord=None):
        """
        Return the appropriate ``PurchaseInfo`` instance.

        This method is not intended to be overridden.
        """
        logging.info("=============== Custom Stratey =============")
        if stockrecord is None:
            stockrecord = self.select_stockrecord(product)
        logging.info(self.pricing_policy(product, stockrecord))
        logging.info(self.pricing_policy(product, stockrecord).__dict__)
        logging.info(stockrecord.__dict__)
        return PurchaseInfo(
            price=self.pricing_policy(product, stockrecord),
            availability=self.availability_policy(product, stockrecord),
            stockrecord=stockrecord)



class DefaultStrategy(strategy.UseFirstStockRecord, strategy.StockRequired, FixedRateTax, Structured):
    """ Default Strategy """


class Selector:
    def strategy(self, request=None, user=None, **kwargs): # pylint: disable=unused-argument
        return DefaultStrategy(request if hasattr(request, 'user') else None)





class Structured1(strategy.Structured):

    def fetch_for_product(self, product, stockrecord=None):
        """
        Return the appropriate ``PurchaseInfo`` instance.

        This method is not intended to be overridden.
        """
        logging.info("=============== Custom Stratey =============")
        if stockrecord is None:
            stockrecord = self.select_stockrecord(product)
        return PurchaseInfo(
            price=self.pricing_policy(product, stockrecord),
            availability=self.availability_policy(product, stockrecord),
            stockrecord=stockrecord)

