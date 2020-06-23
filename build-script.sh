#!/usr/bin/bash -u
organization=test
prefix=perf-test
num_users=${NUM_USERS:-500}
num_tags=${NUM_TAGS:-10}
quay=${QUAY_URL}
token=${TOKEN}

pick=$((1 + RANDOM % ${num_users}))
quay=$QUAY_URL

cat > /tmp/Dockerfile <<EOF
FROM quay.io/jitesoft/alpine:latest

RUN echo "hello" > hello.out
EOF

cd /tmp
podman login ${quay} --tls-verify=false -u ${prefix}_user_${pick} -p password --tmpdir /tmp --root /tmp
podman build --layers --force-rm --tag ${pick} -f /tmp/Dockerfile

echo Pushing image
start=$(date +%s)
podman push --tls-verify=false ${pick} ${quay}/${organization}/${prefix}_repo_${pick}
echo Init : $(($(date +%s) - ${start})) >> /tmp/push-performance.log

if [[ $num_tags -gt 0 ]]; then
    for iter in $(seq 1 $num_tags); do
        cat > /tmp/Dockerfile <<EOF
FROM quay.io/jitesoft/alpine:latest

RUN echo "hello $iter" > hello.out
EOF
        podman build --layers --force-rm --tag $iter -f /tmp/Dockerfile
        start=$(date +%s)
        podman push --log-level=debug --tls-verify=false $iter ${quay}/${organization}/${prefix}_repo_${pick}:test_$iter
        echo Tag : $(($(date +%s) - ${start})) >> /tmp/push-performance.log
    done
fi

cat /tmp/push-performance.log
