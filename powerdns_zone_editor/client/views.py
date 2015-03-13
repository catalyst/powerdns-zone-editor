import copy
import json

import requests

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
from rest_framework.request import Request, clone_request

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
    allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    source = 'servers/%s/zones/%%(pk)s' % settings.POWERDNS_SERVER

    def _user_belongs_to_account(self, user, account):
        return user.is_superuser or user.groups.filter(name=account).exists()

    def _denied_response(self):
        response = Response()
        response.data = ['code', 'error']
        response.status_code = 422
        return response

    def _powerdns_request(self, method, data=None):
        return requests.request(
            method,
            '%s/%s' % (self.get_proxy_host(), self.get_source_path()),
            data=json.dumps(data),
            headers={'X-Api-Key': settings.POWERDNS_API_KEY},
        )

    def proxy(self, request, *args, **kwargs):
        if request.method == 'GET': # load zone
            response = super(ZoneProxyView, self).proxy(request, *args, **kwargs)

            if not self._user_belongs_to_account(request.user, response.data['account']):
                return self._denied_response()

            return response
        elif request.method == 'PUT': # saving a changed zone
            import pprint; pprint.pprint(request.data)
            # XXX this ACL checking code needs tidying up

            put_data = copy.copy(request.data)

            server_zone = self._powerdns_request('get')

            if server_zone.status_code != 200:
                return self._denied_response()

            server_json = server_zone.json()

            if not self._user_belongs_to_account(request.user, server_json['account']):
                return self._denied_response()

            server_records = server_json['records']
            modifications = [record for record in put_data['records'] if 'modification' in record and record['modification'] in ('created', 'updated', 'deleted')]

            key = itemgetter('name', 'type')
            server_rrsets = {
                k: list(v) for k,v in groupby(sorted(server_records, key=key), key=key)
            }

            patched_rrsets = {}

            for modification in modifications:
                if modification['type'].lower() == 'soa':
                    modification['name'] = server_json['name']

                if modification['modification'] == 'updated':
                    original_rrset_key = (modification['original']['name'], modification['original']['type'])
                    server_rrsets[original_rrset_key].remove(modification['original'])
                    patched_rrsets[original_rrset_key] = server_rrsets[original_rrset_key]

                new_rrset_key = (modification['name'], modification['type'])
                new_rrset = patched_rrsets.get(new_rrset_key, server_rrsets.get(new_rrset_key, []))
                new_rr = {k:v for k,v in modification.iteritems() if k not in ('original', 'modification')}

                if 'disabled' not in new_rr:
                    new_rr['disabled'] = False

                if modification['modification'] == 'deleted':
                    new_rrset.remove(new_rr)
                else:
                    new_rrset.append(new_rr)

                patched_rrsets[new_rrset_key] = new_rrset

            patch_request_data = {
                'rrsets': [
                    {
                        'name': k[0],
                        'type': k[1],
                        'changetype': 'REPLACE',
                        'records': v,
                    } for k, v in patched_rrsets.iteritems()
                ]
            }

            patch_request = self._powerdns_request('patch', patch_request_data)
            patch_response = Response(data=patch_request.text)

            return patch_response;

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
