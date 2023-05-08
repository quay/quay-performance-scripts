#!/usr/bin/bash

#
# This script assumes the Quay Operator has deployed Quay and we can modify the database.
# Should contain quaydb.sql snapshot in the same directory to execute this script.
#

# Query app and db pods
quay_ns=quay-enterprise
db=$(oc get pods -n $quay_ns -l quay-component=postgres --no-headers -o name)
app=$(oc -n $quay_ns get pods -l quay-component=quay-app -o name)

# Copy over DB which has the app token generated.
oc -n $quay_ns cp ./quaydb.sql $(echo $db | awk -F/ '{print $2}'):/tmp/database

# Reset Database
oc -n $quay_ns exec $db -- dropdb example-registry-quay-database
oc -n $quay_ns exec $db -- createdb example-registry-quay-database
oc -n $quay_ns exec $db -- sh -c 'psql example-registry-quay-database < /tmp/database'

# Reset the app in case of a DB issue
oc delete $app -n $quay_ns