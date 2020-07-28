#!/usr/bin/bash -u

curl -L https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 > /usr/local/bin/jq
chmod +x /usr/local/bin/jq

prefix=perf-test
uuid=${UUID}
num_users=${NUM_USERS:-30}
rate=${RATE:-10}
quay=${QUAY_URL}
duration=${DURATION:-10}
pick=$((1 + RANDOM % ${num_users}))

prefix=${PREFIX:-perf-test}
elastic=${ES:-search-cloud-perf-lqrf3jjtaqo7727m7ynd2xyt4y.us-west-2.es.amazonaws.com}
es_port=${ES_PORT:-80}
db=${DB:-mysql57}
test_name=${TEST:-performance_test}
quay_version=${QUAY_VERSION:-3}

# Elasticsearch params
export es=$elastic
export es_port=$es_port
export es_index=ripsaw-vegeta
export clustername=quay${quay_version}_${db}_${test_name}

echo "Capture Token"
token_10=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_10_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_100=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_100_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_500=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_500_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_1000=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_1000_tags:pull,push" | jq '.token' | sed -e 's/"//g')
token_10000=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_10000_tags:pull,push" | jq '.token' | sed -e 's/"//g')

# Catalog
echo "+-----------------------+ v2 _catalog +-----------------------+"
path=v2/_catalog
URL=https://${quay}/${path}
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_10" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 _catalog +---------------------+"

# List Tags 10_tags
echo "+-----------------------+ v2 repo with 10 tag +-----------------------+"
path=v2/user/repo_10_tags/tags/list
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_10_tags/tags/list
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_10" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 repo with 10 tag +---------------------+"

# List Tags 100_tags
echo "+-----------------------+ v2 repo with 100 tag +-----------------------+"
path=v2/user/repo_100_tags/tags/list
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_100_tags/tags/list
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_100" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 repo with 100 tag +---------------------+"

# List Tags 500_tags
echo "+-----------------------+ v2 repo with 500 tag +-----------------------+"
path=v2/user/repo_500_tags/tags/list
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_500_tags/tags/list
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_500" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 repo with 500 tag +---------------------+"

# List Tags 1000_tags
echo "+-----------------------+ v2 repo with 1000 tag +-----------------------+"
path=v2/user/repo_1000_tags/tags/list
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_1000_tags/tags/list
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_1000" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 repo with 1000 tag +---------------------+"

# List Tags 10000_tags
echo "+-----------------------+ v2 repo with 10000 tag +-----------------------+"
path=v2/user/repo_10000_tags/tags/list
URL=https://${quay}/v2/${prefix}_user_${pick}/repo_10000_tags/tags/list
echo "GET $URL" | vegeta attack -rate $rate -duration ${duration}s -insecure -header "Authorization: Bearer $token_10000" > /tmp/result.log
cat /tmp/result.log | vegeta report
cat /tmp/result.log | vegeta report --every=1s --type=json --output=/tmp/result.json
run_snafu -t vegeta -r /tmp/result.json  -u ${uuid} --target_name ${path} -w ${rate}
echo "+---------------------+ End v2 repo with 10000 tag +---------------------+"
