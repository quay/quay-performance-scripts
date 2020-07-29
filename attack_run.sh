#!/bin/bash

set -u

export QUAY_URL=<URL>
export UUID=$(uuidgen)
export DURATION=120
export PARALLELISM=10
export NUM_USERS=10
export RATE=40
export PREFIX=perf-test
export ES=search-cloud-perf-lqrf3jjtaqo7727m7ynd2xyt4y.us-west-2.es.amazonaws.com
export ES_PORT=80
export DB=mysql57
export TEST_NAME=perf_test
export QUAY_VERSION=3.3.0


kubectl delete ns quay-perf
kubectl create ns quay-perf
kubectl delete cm run-script -n quay-perf --ignore-not-found
kubectl create cm --from-file=run-script.sh run-script -n quay-perf
kubectl apply -f assets/role.yaml
kubectl apply -f assets/rolebinding.yaml
cat assets/run-vegeta-load.yaml | envsubst > run_job.yaml
kubectl apply -f run_job.yaml
