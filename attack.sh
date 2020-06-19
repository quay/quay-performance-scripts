#!/bin/bash

set -u

export TOKEN=opiqq6KJpCnn4YWqS4kkPku7pohjfzKX10EOGrUi
export QUAY_URL=rook-quay-quay-openshift-quay.apps.rook43quay.perf-testing.devcluster.openshift.com
export PARALLELISM=200
export POD_COUNT=200
export NUM_USERS=500
export NUM_IMAGES=100
export NUM_TAGS=10

kubectl create ns quay-perf
kubectl delete cm load-script -n quay-perf --ignore-not-found
kubectl create cm --from-file=build-script.sh load-script -n quay-perf
kubectl apply -f role.yaml 
kubectl apply -f rolebinding.yaml
cat create-container-image-job.yaml | envsubst > newjob.yaml
kubectl apply -f newjob.yaml

