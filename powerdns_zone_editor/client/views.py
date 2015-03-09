import collections

from django.conf import settings
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_proxy.views import ProxyView

from client import serializers

class PowerDnsProxyView(ProxyView):

    def get_headers(self, request):
        headers = super(PowerDnsProxyView, self).get_headers(request)
        headers['X-Api-Key'] = 'password'
        return headers

    def proxy(self, request, *args, **kwargs):
        user = self.request.user
        response = super(PowerDnsProxyView, self).proxy(request, *args, **kwargs)

        if user.is_superuser:
            return response

        groups = [str(group) for group in user.groups.all()]

        try:
            response.data = [record for record in response.data if 'account' in record and record['account'] in groups or 'account' not in record]
        except TypeError:
            if 'account' in response.data and response.data['account'] not in groups:
                response.data = ['code', 'error']
                response.status_code = 422
        return response

class ZoneListProxy(PowerDnsProxyView):
    source = 'servers/%s/zones' % settings.POWERDNS_SERVER

class ZoneProxy(PowerDnsProxyView):
    source = 'servers/%s/zones/%%(pk)s' % settings.POWERDNS_SERVER

class UserView(APIView):
    def get(self, request):
        return Response({
            'username': request.user.username,
            'groups': [str(group) for group in request.user.groups.all()],
        })
