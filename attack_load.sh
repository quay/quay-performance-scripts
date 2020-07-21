#!/bin/bash

set -u

export QUAY_URL=<URL>
export PREFIX=pref-test
export PARALLELISM=1
export NUM_USERS=1
export CONCURRENT_JOBS=10

kubectl delete ns quay-perf
kubectl create ns quay-perf
kubectl delete cm load-script -n quay-perf --ignore-not-found
kubectl create cm --from-file=targeted-build-script.sh load-script -n quay-perf
kubectl apply -f assets/role.yaml
kubectl apply -f assets/rolebinding.yaml

for i in $(seq 1 ${NUM_USERS}); do
  echo Loading User $i
  export USER=$i
  cat assets/create-container-image-job.yaml | envsubst > /tmp/loadjob$i.yaml
  kubectl apply -f /tmp/loadjob$i.yaml
  if (( $i % ${PARALLELISM} == 0 )); then
    until [[ $(echo $(oc get jobs -n quay-perf -o jsonpath='{.items[*].status.active}') | sed -e 's/ /+/g' | bc) -eq 0 ]]; do
      sleep 60
    done
  fi
done
