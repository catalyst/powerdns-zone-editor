#!/usr/bin/env python

"""
Basic PowerDNS API client class and errors using `requests'.
"""

import json

import requests

class PowerDnsBackendError(Exception):
    pass

class PowerDnsClient(object):
    """
    Client for PowerDNS JSON API.
    """

    def __init__(self, hostname='127.0.0.1', port=8081, api_key=None, server='localhost', accounts=None):
        self.accounts = accounts
        self.hostname = hostname
        self.port = port
        self.api_key = api_key
        self.server = server

    def _request(self, method, path, data=None):
        return requests.request(
            method,
            'http://%s:%i/servers/%s/%s' % (self.hostname, self.port, self.server, path),
            data=json.dumps(data),
            headers={'X-Api-Key': self.api_key},
        )

    def get_zones(self):
        """
        Return a list of all zones, optionally filtered by list of accounts.
        """

        all_zones_request = self._request('GET', 'zones')
        all_zones = all_zones_request.json()

        if all_zones_request.status_code == 200:
            if self.accounts:
                return [zone for zone in all_zones if zone['account'] in self.accounts]
            else:
                return all_zones
        else:
            raise PowerDnsBackendError(('Could not retrieve zone list', all_zones_request.status_code))

    def get_zone(self, zone_id):
        """
        Return a single zone, optionally filtered by list of accounts.
        """

        zone_request = self._request('GET', 'zones/%s' % zone_id)
        zone = zone_request.json()

        if zone_request.status_code == 200:
            if self.accounts:
                if zone['account'] in self.accounts:
                    return zone
                else:
                    return None
            else:
                return zone
        elif zone_request.status_code == 422:
            return None
        else:
            raise PowerDnsBackendError(('Could not retrieve zone %s' % zone_id, zone_request.status_code))

    def patch_zone(self, zone_id, patch_data):
        """
        Patch an existing zone. Does /not/ check that the zone belongs to specified account.
        """

        patch_request = self._request('PATCH', 'zones/%s' % zone_id, patch_data)
        if patch_request.status_code == 200:
            return patch_request.json()
        else:
            raise PowerDnsBackendError(('Could not patch zone %s' % zone_id, zone_request.status_code))
