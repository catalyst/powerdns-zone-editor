import copy
import json

import requests

from operator import itemgetter
from itertools import groupby

from django.db import transaction
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

from client.models import Zone, ZoneRecord

from client.pdns import PowerDnsClient

def pdns_client():
    return PowerDnsClient(api_key=settings.POWERDNS_API_KEY)

def user_groups(user):
    if user.is_superuser:
        return None
    else:
        return [str(group) for group in user.groups.all()]

def denied_response():
    response = Response()
    response.status_code = 403
    return response

def database_record_to_pdns_record(record):
    return {'disabled': False, 'name': record.rr_name, 'type': record.rr_type, 'ttl': record.rr_ttl, 'content': record.rr_content}

class PowerDnsProxyView(ProxyView):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PowerDnsProxyView, self).dispatch(*args, **kwargs)

    def get_headers(self, request):
        headers = super(PowerDnsProxyView, self).get_headers(request)
        headers['X-Api-Key'] = 'password'
        return headers

class ZoneListView(PowerDnsProxyView):
    allowed_methods = ['GET', 'POST']
    source = 'servers/%s/zones' % settings.POWERDNS_SERVER

    def get(self, request, *args, **kwargs):
        response = super(ZoneListView, self).get(request, *args, **kwargs)

        if not request.user.is_superuser:
            response.data = [zone for zone in response.data if request.user.groups.filter(name=zone['account']).exists()]

        return response

class ZoneView(PowerDnsProxyView):
    allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    source = 'servers/%s/zones/%%(pk)s' % settings.POWERDNS_SERVER

    def _user_belongs_to_account(self, user, account):
        return user.is_superuser or user.groups.filter(name=account).exists()

    def _powerdns_request(self, method, data=None):
        return requests.request(
            method,
            '%s/%s' % (self.get_proxy_host(), self.get_source_path()),
            data=json.dumps(data),
            headers={'X-Api-Key': settings.POWERDNS_API_KEY},
        )

    def proxy(self, request, *args, **kwargs):
        if request.method == 'GET': # load zone
            response = super(ZoneView, self).proxy(request, *args, **kwargs)

            if 'account' not in response.data or not self._user_belongs_to_account(request.user, response.data['account']):
                return denied_response()

            return response
        elif request.method == 'PUT': # saving a changed zone
            # XXX this ACL checking code needs tidying up

            put_data = copy.copy(request.data)
            server_zone = self._powerdns_request('get')

            if server_zone.status_code != 200:
                return denied_response()

            server_json = server_zone.json()

            if not self._user_belongs_to_account(request.user, server_json['account']):
                return denied_response()

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

            if patch_request.status_code == 200: # succeeded
                patched_zone = patch_request.json()

                with transaction.atomic():
                    database_zone = Zone(zone_name=patched_zone['id'], user=request.user, comment=request.data['commitMessage'])
                    database_zone.save()
                    ZoneRecord.objects.bulk_create(
                        [ZoneRecord(zone=database_zone, rr_name=record['name'], rr_type=record['type'], rr_ttl=record['ttl'], rr_content=record['content']) for record in patched_zone['records']]
                    )

            patch_response = Response(data=patch_request.text)
            return patch_response

class UserView(APIView):
    def get(self, request):
        return Response({
            'username': request.user.username,
            'groups': user_groups(request.user),
        })

class ZoneRevisionListView(APIView):
    def get(self, request, pk):
        if any([pk == zone['id'] for zone in pdns_client().get_zones(accounts=user_groups(request.user))]):
            revisions = Zone.objects.filter(zone_name=pk).order_by('-created')
            return Response(
                [{'id': revision.id, 'user': revision.user.username, 'created': revision.created, 'comment': revision.comment} for revision in revisions]
            )
        else:
            return denied_response()

class ZoneRevisionView(APIView):
    def get(self, request, zone_id, pk):
        revision_zone = Zone.objects.get(pk=pk)
        server_zone = pdns_client().get_zone(revision_zone.zone_name, accounts=user_groups(request.user))
        diff_records = []

        if server_zone is None:
            return denied_response()

        revision_records = [database_record_to_pdns_record(record) for record in revision_zone.records.all()]

        for revision_record in revision_records:
            if revision_record not in server_zone['records'] and revision_record['type'].lower() != 'soa':
                revision_record['modification'] = 'created'
                diff_records.append(revision_record)

        for server_record in server_zone['records']:
            if server_record not in revision_records and server_record['type'].lower() != 'soa':
                server_record['modification'] = 'deleted'
            diff_records.append(server_record)

        return Response(diff_records)

class ClientView(TemplateView):
    template_name = "client/client.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ClientView, self).dispatch(*args, **kwargs)
