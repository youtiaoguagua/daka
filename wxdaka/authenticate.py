from django.contrib.auth.models import User
from .models import DetailUser
from rest_framework import authentication
from rest_framework import exceptions

class AuthenticationCustomer(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_TOKEN')
        if not token:
            return None
        try:
            user = User.objects.get(detailuser__token=token)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        return (user, None)