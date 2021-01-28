from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ecommerce.core.models import User
import stripe
from django.conf import settings
from oscar.core.loading import get_model

BillingAddress = get_model('order', 'BillingAddress')
Country = get_model('address', 'Country')
stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


class CustomStripeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        API: /stripe_api/profile/?email={email_address}
        This function is used to send the stripe customer_id saved in user context and if it doesn't exist create one and return.
        """
        user = request.user
        if 'customer_id' in user.tracking_context:
            return Response({'message':'', 'status': True, 'result':{'customer_id':user.tracking_context['customer_id']}, 'status_code':200})
        else:
            customer_id = self.create_customer_id(request)
            if customer_id:
                user.tracking_context['customer_id'] = customer_id
                user.save()
                return Response({'message':'', 'status': False, 'result':{'customer_id':customer_id}, 'status_code':400})
            else:
                return  Response({'message':'customer_id not found, please provide a token to continue.', 'status': False, 'result':{}, 'status_code':400})

    def create_customer_id(self, request):
        """
        This function is used to create a customer in stripe and return its customer_id.
        """
        if 'token' in request.POST:
            token = request.POST['token']
            billing_address = self.get_address_from_token(token)
            address = {
            'city': billing_address.line4,
            'country': billing_address.country,
            'line1': billing_address.line1,
            'line2': billing_address.line2,
            'postal_code': billing_address.postcode,
            'state': billing_address.state
            }
            customer = stripe.Customer.create(
                source=token,
                email=request.user.email,
                address=address,
                name=request.user.full_name
            )
            return customer['id']
        else:
            return None

    def get_address_from_token(self,token):
        """ Retrieves the billing address associated with token.

        Returns:
            BillingAddress
        """
        data = stripe.Token.retrieve(token)['card']
        try:
            country = Country.objects.get(iso_3166_1_a2__iexact=data['address_country'])
        except:
            country = "SG"
        address = BillingAddress(
        first_name=data['name'],    # Stripe only has a single name field
        last_name='',
        line1=data['address_line1'],
        line2=data.get('address_line2') or '',
        line4=data['address_city'],  # Oscar uses line4 for city
        postcode=data.get('address_zip') or '',
        state=data.get('address_state') or '',
        country=country
        )
        return address





