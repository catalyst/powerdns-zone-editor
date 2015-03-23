import json

import requests

class PowerDnsBackendError(Exception):
    pass

class PowerDnsClient(object):

    def __init__(self, hostname='127.0.0.1', port=8081, api_key=None, server='localhost'):
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

    def get_zones(self, accounts=None):
        all_zones_request = self._request('GET', 'zones')
        all_zones = all_zones_request.json()

        if all_zones_request.status_code == 200:
            if accounts:
                return [zone for zone in all_zones if zone['account'] in accounts]
            else:
                return all_zones
        else:
            raise PowerDnsBackendError(('Could not retrieve zone list', all_zones_request.status_code))

    def get_zone(self, zone_id, accounts=None):
        zone_request = self._request('GET', 'zones/%s' % zone_id)
        zone = zone_request.json()

        if zone_request.status_code == 200:
            if accounts:
                if zone['account'] in accounts:
                    return zone
                else:
                    return None
            else:
                return zone
        elif zone_request.status_code == 422:
            return None
        else:
            raise PowerDnsBackendError(('Could not retrieve zone', zone_request.status_code))
