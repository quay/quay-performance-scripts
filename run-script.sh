#!/usr/bin/bash -u

prefix=perf-test
num_users=${NUM_USERS:-30}
rate=${RATE:-10}
quay=${QUAY_URL}
duration=${DURATION:-10}
pick=$((1 + RANDOM % ${num_users}))

echo "Capture Token"
token_10=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_10_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_100=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_100_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_500=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_500_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_1000=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_1000_tags:pull,push" | jq '.token' | sed -e 's/"//g')

# Catalog
echo "+-----------------------+ v2 _catalog +-----------------------+"
URL=https://${quay}/v2/_catalog
echo "GET $URL" | ./vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_10" | ./vegeta report
echo "+---------------------+ End v2 _catalog +---------------------+"

# List Tags 10_tags
echo "+-----------------------+ v2 repo with 10 tag +-----------------------+"
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_10_tags/tags/list
echo "GET $URL" | ./vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_10" | ./vegeta report
echo "+---------------------+ End v2 repo with 10 tag +---------------------+"

# List Tags 100_tags
echo "+-----------------------+ v2 repo with 100 tag +-----------------------+"
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_100_tags/tags/list
echo "GET $URL" | ./vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_100" | ./vegeta report
echo "+---------------------+ End v2 repo with 100 tag +---------------------+"

# List Tags 500_tags
echo "+-----------------------+ v2 repo with 500 tag +-----------------------+"
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_500_tags/tags/list
echo "GET $URL" | ./vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_500" | ./vegeta report
echo "+---------------------+ End v2 repo with 500 tag +---------------------+"

# List Tags 1000_tags
echo "+-----------------------+ v2 repo with 1000 tag +-----------------------+"
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_1000_tags/tags/list
echo "GET $URL" | ./vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_1000" | ./vegeta report
echo "+---------------------+ End v2 repo with 1000 tag +---------------------+"
