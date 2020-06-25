#!/bin/bash

set -u

export TOKEN=<TOKEN>
export QUAY_URL=<URL>
export PARALLELISM=10
export POD_COUNT=1000
export NUM_USERS=1000

kubectl delete ns quay-perf
kubectl create ns quay-perf
kubectl delete cm load-script -n quay-perf --ignore-not-found
kubectl create cm --from-file=targeted-build-script.sh load-script -n quay-perf
kubectl apply -f assets/role.yaml
kubectl apply -f assets/rolebinding.yaml
cat assets/create-container-image-job.yaml | envsubst > newjob.yaml
kubectl apply -f newjob.yaml
