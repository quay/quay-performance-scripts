# Quay Perf Testing

## Quick Start

The following steps can help you quickly get started with running the
Quay Performance Test suite.

**Setup**

- Deploy Quay to an Openshift Cluster using the Quay Operator. 
- Create a Route or LoadBalancer pointing to the Quay Service
- In Quay, perform the following steps:
  - Create a user called `admin`
  - Login as `admin`
  - Create an organization called `test`
  - Within that organization, create an application called `test`
  - Within that application, navigate to "Generate Token"
  - Select all check-boxes to grant full privileges and click "Generate Access Token"
  - Store the access token. It will be used in later steps.
- Create a VM located near your Openshift Cluster. For example, it may be
  an AWS ec2 instance in the same region. This will be used for running the
  tests.
- Ensure the following packages are installed
  - `wget`
  - `python >= 3.6`
  - `git`
  - `oc` [Download Link](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz)
  - `jq`
  - `bc`
- SSH into the VM.
- Clone this repository: `git clone https://github.com/quay/quay-performance-scripts.git`
- Install the test tools: `cd quay-performance-scripts; ./install.sh`
- Modify `attack_load.sh` to set the following variables:
  - `QUAY_URL=<url of quay>` (Note: Do not prefix http or https)
- Modify `attack_run.sh` to set the following variables:
  - `QUAY_URL=<url of quay>`
- Modify `quay_vegeta_load.sh` or set environment variables to override the defaults.
  - Change `NAMESPACE` to reflect the namespace the tests should use

**Execute Tests**

At this point, everything should be configured. You'll need the Access Token you created earlier in Quay. Run the following commands sequentially. I recommend running these commands in a `tmux` or GNU `screen` session to avoid interrupting tests if you are disconnected.

- `quay_vegeta_load.sh <https://quay url> <access token>`
- `attack_load.sh`
- `attack_run.sh`

Assuming no errors were encountered, the results from your tests will be displayed through STDOUT. They will also be pushed to the ElasticSearch host mentioned in the *.sh files.

## Additionall Tooling
This script assumes the Vegeta binary is colocated with the scripts.

### Tool install script

If you run the `install.sh`, the python venv will be placed into `/tmp/quay_venv` unless the user overrides the
env var, `VENV`.

This script also pulls the vegeta binary, and places it in the `quay-performance-scripts` directory.

### Manual install

#### To install Vegeta simply

```
$ wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
$ tar -xzf vegeta-12.8.3-linux-amd64.tar.gz
```

This will drop in an binary which we will execute with the scripts.

#### Install SNAFU on the node running quay_vegeta_load.sh

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
labels=${LABELS:-false}			# If the user as applied labeles for the quay app and quay db on the nodes (see below)..
namespace=${NAMESPACE:-quay-mysql57}	# Namespace to launch pods to collect metadata
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

To help have targted metadata collection, set labels on the nodes where Quay is running. For the `quay-app` use quay:app and for the node where the db is located
use `quay:db`.

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
