#!/usr/bin/bash
set -x

organization=test
prefix=perf-test
num_users=1000
num_tags=100

pick=$((1 + RANDOM % 1000))
quay=$QUAY_URL

cat > /tmp/Dockerfile <<EOF
FROM registry.access.redhat.com/ubi8:latest

RUN mkdir -pv /tmp/test
RUN echo "hello" > /tmp/test/hello.out
EOF

podman login ${quay} --tls-verify=false -u ${prefix}_user_${pick} -p password
podman build --layers --force-rm --tag ${quay}/${organization}/${prefix}_repo_${pick} -f /tmp/Dockerfile
podman push ${quay}/${organization}/${prefix}_repo_${pick} --tls-verify=false

if [[ $num_tags -gt 0 ]]; then
    for iter in $(seq 1 $num_tags); do
        cat > /tmp/Dockerfile_$iter <<EOF
FROM registry.access.redhat.com/ubi8:latest

RUN mkdir -pv /tmp/test
RUN echo "hello $iter" > /tmp/test/hello.out
EOF
        podman build --layers --force-rm --tag ${quay}/${organization}/${prefix}_repo_${pick}:test_$iter -f /tmp/Dockerfile_$iter
	podman push ${quay}/${organization}/${prefix}_repo_${pick}:test_$iter --tls-verify=false
    done
fi
