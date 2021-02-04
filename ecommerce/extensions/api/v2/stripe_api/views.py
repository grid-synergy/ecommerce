from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ecommerce.core.models import User
import stripe
from django.conf import settings
from oscar.core.loading import get_model
import logging

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

class PaymentView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        email = request.user.email
        customer_data = stripe.Customer.list(email=email).data
        user_basket = request.basket
        if len(customer_data) > 0:
            if user_basket.status == "Open":
                total_ammount = int(user_basket.total_incl_tax)
                if total_ammount > 0:
                    payment_data = stripe.Charge.create(
                        amount=total_ammount, currency='sgd',customer=customer_data[0],
                        )
                    if payment_data.paid:
                        user_basket.status = "Submitted"
                        user_basket.save()
                        return Response({"message":"Payment completed.", "status": True, "result":payment_data, "status_code":200})
                    else:
                        return Response({"message":payment_data.failure_message, "status": False, "result":{}, "status_code":400})
                else:
                    return Response({"message":"Total ammount must be greater than 0.", "status": False, "result":{}, "status_code":400})
            else:
                return Response({"message":"No item found in cart.", "status": False, "result":{}, "status_code":400})
        else:
            return Response({'message':'customer not found.', 'status': False, 'result':{}, 'status_code':400})

class TokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        if 'token' in user.tracking_context:
            return Response({'message':'', 'status': True, 'result':{'token':user.tracking_context['token']}, 'status_code':200})
        else:
            return Response({'message':'Token not found', 'status': False, 'result':{'token': None}, 'status_code':400})
