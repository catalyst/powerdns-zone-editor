from itertools import groupby
from operator import itemgetter
import copy
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import requests

from client.models import Zone, ZoneRecord
from client.pdns import PowerDnsClient

def pdns_client(accounts):
    return PowerDnsClient(
        accounts=accounts,
        server=settings.POWERDNS['server'],
        hostname=settings.POWERDNS['hostname'],
        port=settings.POWERDNS['port'],
        api_key=settings.POWERDNS['api-key'],
    )

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

class ZonesListView(APIView):
    allowed_methods = ['GET', 'POST']
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        zones = pdns_client(accounts=user_groups(request.user)).get_zones()
        return Response(zones)

class ZoneView(APIView):
    allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        zone = pdns_client(accounts=user_groups(request.user)).get_zone(pk)

        if not zone:
            return denied_response()

        return Response(zone)

    def put(self, request, pk):
        import pprint; pprint.pprint(json.dumps(request.data))

        client = pdns_client(accounts=user_groups(request.user))
        put_data = copy.copy(request.data)
        server_zone = client.get_zone(pk)

        if not server_zone:
            return denied_response()

        server_records = server_zone['records']
        modifications = [record for record in put_data['records'] if 'modification' in record and record['modification'] in ('created', 'updated', 'deleted')]

        key = itemgetter('name', 'type')
        server_rrsets = {
            k: list(v) for k,v in groupby(sorted(server_records, key=key), key=key)
        }

        patched_rrsets = {}

        for modification in modifications:
            if modification['type'].lower() == 'soa':
                modification['name'] = server_zone['name']

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

        patch_request = client.patch_zone(pk, patch_request_data)

        if patch_request: # succeeded
            with transaction.atomic():
                database_zone = Zone(zone_name=patch_request['id'], user=request.user, comment=request.data['commitMessage'])
                database_zone.save()
                ZoneRecord.objects.bulk_create(
                    [ZoneRecord(zone=database_zone, rr_name=record['name'], rr_type=record['type'], rr_ttl=record['ttl'], rr_content=record['content']) for record in patch_request['records']]
                )

        patch_response = Response(patch_request)
        return patch_response

class UserView(APIView):
    allowed_methods = ['GET']
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({
            'username': request.user.username,
            'groups': user_groups(request.user),
        })

class ZoneRevisionListView(APIView):
    allowed_methods = ['GET']
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        if any([pk == zone['id'] for zone in pdns_client(accounts=user_groups(request.user)).get_zones()]):
            revisions = Zone.objects.filter(zone_name=pk).order_by('-created')
            return Response(
                [{'id': revision.id, 'user': revision.user.username, 'created': revision.created, 'comment': revision.comment} for revision in revisions]
            )
        else:
            return denied_response()

class ZoneRevisionView(APIView):
    allowed_methods = ['GET']
    permission_classes = (IsAuthenticated,)

    def get(self, request, zone_id, pk):
        revision_zone = Zone.objects.get(pk=pk)
        server_zone = pdns_client(accounts=user_groups(request.user)).get_zone(revision_zone.zone_name)
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
