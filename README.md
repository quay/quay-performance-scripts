# Quay Perf Testing
## Assumptions
The Quay Operator has been deployed.

## Additionall Tooling
This script assumes the Vegeta binary is colocated with the scripts.

### To install Vegeta simply

```
$ wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
$ tar -xzf vegeta-12.8.3-linux-amd64.tar.gz
```

This will drop in an binary which we will execute with the scripts.

### Install SNAFU on the node running quay_vegeta_load.sh

git clone the snafu repo

```
 $ git clone https://github.com/cloud-bulldozer/snafu
```

Note: You must have at least python3.6 installed.

After you have copied the repo, install the python application.

```
 $ python3.6 setup.py develop
```


## Workflow
Once Quay has been deployed and the superuser/application token has been generated the performance workloads can be ran.

The `attack_load.sh` and `attack_run.sh` assume we have K8s infrastucture to run the load testing.

```
    User creation
[ quay_vegeta_load.sh ]
        |
        |
        ↓
    Load Repos
[ attack_load.sh ]
        |
        |
        ↓
  Run Load Test
[ attack_run.sh ]

```

### User creation : quay_vegeta_load.sh

Variables to edit or review

```
org=${ORG:-test}			# In the creation of the superuser/application you create an origanization which the application lives under.
password=${PASSWORD:-password}		# password we should update the user accounts with
target_num=${TARGET:-1000}		# Number of accounts to create
rate=${RATE:-50}			# Rate of creation
prefix=${PREFIX:-perf-test}		# What to prefix to use for the accounts ie perf-test_user_XX
elastic=${ES:-es-server} 		# Elasticsearch server to send latency data
es_port=${ES_PORT:-80}			# Elasticserach port, usual 9200
db=${DB:-mysql57}			# What was the backend database
test_name=${TEST:-performance_test}	# Describe the test or the env
quay_version=${QUAY_VERSION:-3}		# Version of quay
```

Either you can modify the variables in the script or simply set them with :

```
export ORG=test
```

Once those values are updated, execute the `quay_vegeta_load.sh` script. Passing the quay URL and the superuser application token.

Example execution:

```
$ root@ip-172-31-66-66: ~/quay_perf # time ./quay_vegeta_load.sh https://quay-testing.cluster.dev <api-key>
```

### Load Quay with repos and tags : attack_load.sh ->  targeted-build-script.sh

Variables to edit or review
```
export QUAY_URL=<URL>		# Remove https, simply pass the URL without https
export PREFIX=pref-test 	# Prefix used above to create the accounts
export PARALLELISM=1    	# How many concurrent jobs to run?
export NUM_USERS=1		# How many users to load up
export CONCURRENT_JOBS=10	# How many tags to generate at once in each job
```

Script that will create 5 repos by default, each with different amount of tags:

- Repo with 10 tags
- Repo with 100 tags
- Repo with 500 tags
- Repo with 1000 tags
- Repo with 10000 tags

This script will choose a random user to build all the above with.

## Database
The database provided here is a dump from psql with a token generated for organization `test`

## Token
The default token is `opiqq6KJpCnn4YWqS4kkPku7pohjfzKX10EOGrUi`, after running the `quay_init.sh` script run the following

```
$ curl -k -X GET -H "Authorization: Bearer opiqq6KJpCnn4YWqS4kkPku7pohjfzKX10EOGrUi"  https://rook-quay-quay-openshift-quay.apps.rook43quay.perf-testing.devcluster.openshift.com/api/v1/superuser/users/
{"users": [{"username": "quay", "kind": "user", "verified": true, "name": "quay", "super_user": true, "enabled": true, "email": "changeme@example.com", "avatar": {"color": "#8c6d31", "kind": "user", "hash": "5cc105f67a24cab8379ad1cfd5dfdebb", "name": "quay"}}]}
```
