

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from opaque_keys.edx.keys import CourseKey
from decimal import Decimal as D
import numpy as np

register = template.Library()



@register.filter(name='subtract')
def subtract(value, arg):
    return value - arg

@register.filter(name='subtract_tax_from_discount')
def subtract_tax_from_discount(amount):
    tax_percent = settings.LHUB_TAX_PERCENTAGE
    incl_amount = amount
    excl_amount = amount * D(tax_percent/100)
    excl_amount = amount - excl_amount
    excl_amount = "%.2f" % excl_amount
    excl_amount = excl_amount
    inc = 0.01

    for x in np.arange(D(excl_amount), D(incl_amount), D(inc)):
        discount_without_tax = "%.2f" % x
        calc_percent = D(discount_without_tax) * D(tax_percent/100)
        calc_percent = "%.2f" % calc_percent
        actual_tax = D(discount_without_tax) + D(calc_percent)
        if actual_tax == amount:
            return discount_without_tax


@register.filter(name='tax_percent')
def tax_percent(total):
    tax_percent = str(settings.LHUB_TAX_PERCENTAGE)
    tax_percent = "GST " + tax_percent + "%"
    return tax_percent

@register.simple_tag
def settings_value(name):
    """
    Retrieve a value from settings.

    Raises:
        AttributeError if setting not found.
    """
    return getattr(settings, name)


@register.tag(name='captureas')
def do_captureas(parser, token):
    """
    Capture contents of block into context.

    Source:
        https://djangosnippets.org/snippets/545/

    Example:
        {% captureas foo %}{{ foo.value }}-suffix{% endcaptureas %}
        {% if foo in bar %}{% endif %}
    """

    try:
        __, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)


@register.filter(name='course_organization')
def course_organization(course_key):
    """
    Retrieve course organization from course key.

    Arguments:
        course_key (str): Course key.

    Returns:
        str: Course organization.
    """
    return CourseKey.from_string(course_key).org


class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = mark_safe(self.nodelist.render(context).strip())
        context[self.varname] = output
        return ''
