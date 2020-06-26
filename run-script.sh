#!/usr/bin/bash -u
set -x

organization=test
prefix=perf-test
num_users=${NUM_USERS:-1000}
rate=${RATE:-10}
quay=${QUAY_URL}
duration=${DURATION:-60}
token=${TOKEN}
pick=$((1 + RANDOM % ${num_users}))

repo_tag_target=api/v1/repository/${organization}/${prefix}_repo_${pick}/tag/

echo "Running against tag endpoint"
echo "GET https://${quay}/${repo_tag_target}" | vegeta attack -insecure -rate ${rate} -duration=${duration}s | tee report.data | vegeta report

