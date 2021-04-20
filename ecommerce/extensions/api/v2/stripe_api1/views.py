from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

class CountItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        logging.info("+_+_+_+_+_+_+_+_+_+_+_+_+_+_+ %s", dir(request.basket))
        return Response({"found":True})

