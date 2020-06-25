#!/usr/bin/bash -u
organization=test
prefix=perf-test
num_users=${NUM_USERS:-500}
num_tags=${NUM_TAGS:-10}
num_repo=${NUM_REPO:-10}
quay=${QUAY_URL}
token=${TOKEN}

repos="10_tags 100_tags 500_tags 1000_tags"

pick=$((1 + RANDOM % ${num_users}))
quay=$QUAY_URL

cat > /tmp/Dockerfile <<EOF
FROM quay.io/jitesoft/alpine:latest

RUN echo "hello" > hello.out
EOF

for repo in $repos; do

  cd /tmp
  podman login ${quay} --tls-verify=false -u ${prefix}_user_${pick} -p password
  podman build --layers --force-rm --tag ${pick} -f /tmp/Dockerfile
  podman tag ${pick} ${quay}/${prefix}_user_${pick}/repo_${repo}

  echo Pushing image
  start=$(date +%s)
  podman push --tls-verify=false ${quay}/${prefix}_user_${pick}/repo_${repo}
  echo Init : $(($(date +%s) - ${start})) >> /tmp/push-performance.log

  num_tags=$(echo ${repo} | awk -F_ '{print $1}')

if [[ $num_tags -gt 0 ]]; then
    for iter in $(seq 1 $num_tags); do
        cat > /tmp/Dockerfile <<EOF
FROM quay.io/jitesoft/alpine:latest

RUN echo "hello $iter" > hello.out
EOF
        podman build --layers --force-rm --tag $iter -f /tmp/Dockerfile
        podman tag ${iter} ${quay}/${prefix}_user_${pick}/repo_${repo}:$iter
        start=$(date +%s)
        podman push --tls-verify=false ${quay}/${prefix}_user_${pick}/repo_${repo}:$iter
        echo Tag : $(($(date +%s) - ${start})) >> /tmp/push-performance.log
    done
fi
done

cat /tmp/push-performance.log
