from operator import itemgetter
from itertools import groupby

from django.http import Http404
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_proxy.views import ProxyView

from client import serializers

class PowerDnsProxyView(ProxyView):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PowerDnsProxyView, self).dispatch(*args, **kwargs)

    def get_headers(self, request):
        headers = super(PowerDnsProxyView, self).get_headers(request)
        headers['X-Api-Key'] = 'password'
        return headers

class ZoneListProxyView(PowerDnsProxyView):
    allowed_methods = ['GET', 'POST']
    source = 'servers/%s/zones' % settings.POWERDNS_SERVER

    def get(self, request, *args, **kwargs):
        response = super(ZoneListProxyView, self).get(request, *args, **kwargs)

        if not request.user.is_superuser:
            response.data = [zone for zone in response.data if request.user.groups.filter(name=zone['account']).exists()]

        return response

class ZoneProxyView(PowerDnsProxyView):
    allowed_methods = ['GET', 'PUT', 'DELETE', 'PATCH']
    source = 'servers/%s/zones/%%(pk)s' % settings.POWERDNS_SERVER

    def get(self, request, *args, **kwargs):
        response = super(ZoneProxyView, self).get(request, *args, **kwargs)

        if not request.user.is_superuser and not request.user.groups.filter(name=response.data['account']).exists():
            response.data = ['code', 'error']
            response.status_code = 422
            return response

        records = response.data['records']

        key = itemgetter('name', 'type')
        rrsets = groupby(sorted(records, key=key), key=key)

        response.data['rrsets'] = [{'name': k[0], 'type': k[1], 'records': list(v)} for k, v in rrsets]

        return response

class UserView(APIView):
    def get(self, request):
        return Response({
            'username': request.user.username,
            'groups': [str(group) for group in request.user.groups.all()],
        })

class ClientView(TemplateView):
    template_name = "client/client.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ClientView, self).dispatch(*args, **kwargs)
