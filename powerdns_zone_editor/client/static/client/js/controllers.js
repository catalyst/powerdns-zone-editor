function ZonesListCtrl($scope, user, zones) {
    $scope.user = user;
    $scope.zones = zones;
}

function ZoneCtrl($scope, $filter, Restangular, user, zone, revisions) {
    $scope.user = user;
    $scope.zone = zone;
    $scope.revisions = revisions;
    $scope.powerdnsError = '';
    $scope.powerdnsResult = '';
    $scope.zone.commitMessage = '';

    $scope.currentRevisionPage = 0;

    $scope.recordTypes = {
        'SOA': {'allowCreate': false, 'required': true, 'sortWeight': -100},
        'A': {},
        'AAAA': {},
        'NS': {'sortWeight': -50},
        'CNAME': {},
        'DNAME': {},
        'MR': {},
        'PTR': {},
        'HINFO': {},
        'MX': {},
        'TXT': {},
        'RP': {},
        'AFSDB': {},
        'SIG': {},
        'KEY': {},
        'LOC': {},
        'SRV': {},
        'CERT': {},
        'NAPTR': {},
        'DS': {'sortWeight': -50},
        'SSHFP': {},
        'RRSIG': {},
        'NSEC': {},
        'DNSKEY': {},
        'NSEC3': {},
        'NSEC3PARAM': {},
        'TLSA': {},
        'SPF': {},
        'DLV': {},
    };

    $scope.refreshRevisions = function() {
        Restangular.one('zones', $stateParams.id).all('revisions').getList().then(function (revisions) {
            _.extend($scope.revisions, revisions);
        });
    };

    $scope.loadRevision = function(revision_created, revision_user, revision_id) {
        Restangular.one('zones', $scope.zone.id).one('revisions', revision_id).get().then(function (revision) {
            var revision_string = $filter('date')(revision_created, 'yyyy-MM-dd HH:mm:ss') + ' by ' + revision_user;
            if (angular.equals(revision, $scope.zone.records)) {
                $scope.powerdnsResult = 'Selected revision ' + revision_string + ' is identical to the current view.';
            } else {
                $scope.zone.records = angular.copy(revision);
                $scope.zone.commitMessage = 'Rolled back to revision ' + revision_string;
                $scope.powerdnsResult = 'Loaded revision ' + revision_string + '.';
            }
        });
    }

    $scope.saveZone = function() {
        $scope.zone.commitMessage = $.trim($scope.zone.commitMessage);

        if ($scope.zone.commitMessage == '') {
            $scope.zone.commitMessage = 'Updated ' + $scope.zone.name;
        }

        $scope.zone.save().then(function (saved_zone) {
            response = angular.fromJson(saved_zone);
            if ('error' in response) {
                $scope.powerdnsError = response.error;
                $scope.powerdnsResult = '';
            } else {
                _.extend($scope.zone, response);
                $scope.zone.commitMessage = '';
                $scope.powerdnsResult = 'Saved zone';
                $scope.powerdnsError = '';
                $scope.refreshRevisions();
            }
        });
    };

    $scope.sortByType = function(record) {
        if (record.modification == 'created' || record.modification == 'creating') {
            return -1;
        }
        recordType = $scope.recordTypes[record.type]
        if ('sortWeight' in recordType) {
            return recordType.sortWeight;
        } else {
            return record.type;
        }
    };

    $scope.countUnsavedRecords = function(modification) {
        return $filter('filter')($scope.zone.records, {'modification': modification}).length;
    };

    $scope.anyUnsavedRecords = function() {
        return $scope.countUnsavedRecords('created') + $scope.countUnsavedRecords('updated') + $scope.countUnsavedRecords('deleted');
    };

    /* Validate input and store the 'pristine' version of the
       record if this is the first time it's been modified */
    $scope.beforeUpdateRecord = function(record, changes) {
        if (changes.name == '' || changes.content == '' || changes.ttl < 60) {
            return 'Record missing fields';
        }

        if (record.modification == 'creating') {
            record.modification = 'created';
        }

        /* Newly created records do not have a 'pristine' version to
           store */
        if (record.modification == 'created') {
            return;
        }

        /* Copy the un-modified state of the record in to a property
           of the record itself */
        if (!record.hasOwnProperty('original')) {
            record.original = angular.copy(record);
            record.modification = 'updated';
        }
    };

    /* If the user has returned the record back to its pristine state
       remove the attribute marking it as having been updated */
    $scope.afterUpdateRecord = function(record) {
        if (record.modification == 'created') {
            return;
        }

        /* Make a copy of the record with the extra attributes removed
           for comparison */
        var record_without_original = angular.copy(record);
        delete record_without_original['original'];
        delete record_without_original['modification'];

        if (angular.equals(record_without_original, record.original)) {
            delete record['original'];
            delete record['modification'];
        }
    };

    /* Toggle marking the record for deletion (in its original form),
       or just remove it if the record only exists locally */
    $scope.deleteRecord = function(record) {
        // 'created' records only exist locally
        if (record.modification == 'created' || record.modification == 'creating') {
            $scope.zone.records.splice($scope.zone.records.indexOf(record), 1);
            return;
        }

        // if the record is already marked for deletion, un-mark it
        if (record.modification == 'deleted') {
            delete record['modification'];
        } else {
            $scope.resetRecord(record);
            record.modification = 'deleted';
        }
    };

    /* Return a record to its pristine state, or remove it if it
       only exists locally */
    $scope.resetRecord = function(record) {
        if (record.modification == 'created' || record.modification == 'creating') {
            $scope.deleteRecord(record);
        }

        if (record.hasOwnProperty('original')) {
            // XXX why is this madness necessary...
            record.name = record.original.name;
            record.type = record.original.type;
            record.ttl = record.original.ttl;
            record.content = record.original.content;
            delete record['original'];
            delete record['modification'];
        }
    };

    $scope.addRecord = function() {
        var created = {
          name: '',
          type: 'A',
          ttl: 3600,
          content: '',
          modification: 'creating'
        };
        $scope.zone.records.push(angular.copy(created));
    };

    $scope.keypress = function(e, form) {
        if (e.which === 13) {
            // slightly horrible way to focus the next row
            $(e.originalEvent.originalTarget).parent().parent().parent().parent().next('tr').find('input').first().focus();
            form.$submit();
        }
    };

}
