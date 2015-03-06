angular.module('dnsApp.controllers', []).controller('ServerListController', function($scope, servers) {
    $scope.servers = servers;
}).
controller('ServerZonesListController', function($scope, server, zones) {
    $scope.server = server;
    $scope.zones = zones;
}).
controller('ServerZoneController', function($scope, zone) {
    $scope.zone = zone;
});
