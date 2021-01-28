from ecommerce.core.models import User
from rest_framework.response import Response
import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import stripe
from django.conf import settings
from oscar.core.loading import get_model
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import	 IsAuthenticated
import stripe
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
import logging
from django.http import Http404

@api_view()
@authentication_classes((JwtAuthentication,))
@permission_classes([IsAuthenticated])
def get_ephemeral_key(request):

    """
    API: /stripe_api/profile/?email={email_address}
    This function is used to send the stripe customer_id saved in user context and if it doesn't exist create one and return.
    """
    try:
        stripe_customer_id = request.GET.get('stripe_customer_id')
        key = stripe.EphemeralKey.create(customer=stripe_customer_id,stripe_version='2020-08-27')
        response = {'message': '' , 'status': True, 'result':key, 'status_code':200}
        return Response(response)
    except Exception as e:
        logging.info('========== e =======')
        logging.info(e)
        return Response(str(e))

