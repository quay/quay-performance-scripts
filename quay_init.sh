#!/usr/bin/bash

#
# This script assumes the Quay Operator has deployed Quay and we can modify the database.
#

quay_ns=openshift-quay
db=$(oc get pods -n $quay_ns -l quay-enterprise-component=quay-database --no-headers -o name)
app=$(oc -n $quay_ns get pods -l quay-enterprise-component=app -o name)

# Copy over DB which has the app token generated
oc -n $quay_ns cp ./assets/quaydb $(echo $db | awk -F/ '{print $2}'):/tmp/database

# Reset Database
oc -n $quay_ns exec $db -- dropdb quay
oc -n $quay_ns exec $db -- createdb quay
oc -n $quay_ns exec $db -- sh -c 'psql quay < /tmp/database'

# Reset the app in case of a DB issue
oc delete $app
