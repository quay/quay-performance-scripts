#!/bin/bash

set -u

export QUAY_URL=<URL>
export PARALLELISM=10
export NUM_USERS=1000
export RATE=10

kubectl delete ns quay-perf
kubectl create ns quay-perf
kubectl delete cm run-script -n quay-perf --ignore-not-found
kubectl create cm --from-file=run-script.sh run-script -n quay-perf
kubectl apply -f assets/role.yaml
kubectl apply -f assets/rolebinding.yaml
cat assets/run-vegeta-load.yaml | envsubst > run_job.yaml
kubectl apply -f run_job.yaml
