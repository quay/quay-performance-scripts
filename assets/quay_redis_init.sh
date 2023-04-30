#!/usr/bin/bash

#
# This script assumes the Quay Operator has deployed Quay and we can modify the database.
#

# Query redis pod
quay_ns=quay-enterprise
redis=$(oc get pods -n $quay_ns -l quay-component=redis --no-headers -o name)

# Reset the app in case of a DB issue
oc delete $redis -n $quay_ns