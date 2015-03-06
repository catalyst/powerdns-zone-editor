angular.module('dnsApp.services',[]).factory('Server', ['$resource', function($resource){
    return $resource('/api/servers/:id'), {id: '@id'}, {
        zones: {method: 'GET', url: '/api/servers/:server/zones'},
        zone: {method: 'GET', url: '/api/servers/:server/zones/:id'},
    };
});
