angular.module('dnsApp', ['ui.router', 'restangular', 'dnsApp.controllers']);

angular.module('dnsApp').config(function($stateProvider, RestangularProvider) {
    $stateProvider.state('servers', {
        url: '/servers',
        templateUrl: 'partials/servers.html',
        controller: 'ServerListController',
        resolve: {
            servers: function (Restangular) {
                return Restangular.allUrl('servers').getList();
            }
        }
    }).
    state('serverZones', {
        url: '/servers/:id',
        templateUrl: 'partials/serverZones.html',
        controller: 'ServerZonesListController',
        resolve: {
            server: function (Restangular, $stateParams) {
                return Restangular.one('servers', $stateParams.id).get();
            },
            zones: function (Restangular, $stateParams) {
                return Restangular.one('servers', $stateParams.id).getList('zones');
            }
        }
    }).
    state('serverZone', {
        url: '/servers/:server_id/zones/:id',
        templateUrl: 'partials/serverZone.html',
        controller: 'ServerZoneController',
        resolve: {
            zone: function (Restangular, $stateParams) {
                return Restangular.one('servers', $stateParams.server_id).one('zones', $stateParams.id).get();
            }
        }
    });
    RestangularProvider.setBaseUrl('/api');
});
