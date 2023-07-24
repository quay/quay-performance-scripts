# Quay Performance Tests

## Description

The purpose of this repository is to provide a set of scalability and
performance tests for Red Hat Quay and Project Quay. These tests are intended to necessarily push Quay to its limits and collect metrics on
various operations. These metrics are used to determine how changes to Quay
affects its performance.

## Quickstart

The test suite is designed to run on openshift platform using a simple configuration file. We just have to set the required parameters and trigger it. More details will be shared below.

## Prerequisites
- Deploy a Openshift environment. The tests will run within the cluster.
- Deploy Quay, itself.
- In Quay, as a superuser (important), create an organization for testing
  purposes. Within that organization, create an application for testing
  purposes. Within that application, create an OAuth Token with all
  permissions (checkboxes) granted. Hold on to this token as it will be used
  later.
- Once after the quay application is deployed. Do a `pg_dump` in the quay postgres pod to capture the initial snapshot into a sql file and keep it copied at `assets/quaydb.sql`.

## Running tests

### Building

From the main directory, the podman image can be built and published to your remote repository (if required) using the below commands: 

```bash
podman build . -t quay-load; 
podman tag localhost/quay-load:latest quay.io/<path-to-yourrepo>:latest; 
podman push quay.io/<path-to-yourrepo>:latest
```

### Running tests on openshift platform

Before running the tests, we need to make sure we are running `assets/quay_init.sh` to reset the postgres database with the initial snapshot and `assets/quay_redis_init.sh` to clear the redis cache.

> **NOTE**: We need to have a file at `assets/quaydb.sql` in order to run `assets/quay_init.sh` which is the snapshot captured when deployed quay initially.

Now once we have the system ready, Deploy `deploy/test.job.yaml` on your openshift cluster. It takes below ENVS as arguments.
### **Envs**
* `QUAY_HOST` - Sting. Indicating quay host url to perform testing.
* `QUAY_OAUTH_TOKEN` - String. Application oauth token created in the prerequisites step.
* `QUAY_ORG`- String. Specifies the test organization.
* `ES_HOST` - String. Elastic search host url.
* `ES_PORT` - String. Elastic search port number.
* `ES_INDEX` - String. Elastic search index to store the results.
* `PUSH_PULL_IMAGE` - Image which contains source code and used in push/pull jobs for testing purposes. Same image that is used for load testing i.e `quay-load` in our case.
* `PUSH_PUSH_ES_INDEX` - ES index to store quay push/pull results. It is separate as it follows different document structure.
* `PUSH_PULL_NUMBERS` - The amount of images to do push/pull operations on.
* `TARGET_HIT_SIZE` - String. Indicates the total amount of requests to hit the system with.
* `CONCURRENCY` - String. Indicates the rate(concurrency) at which the requests hits must happen in parallel.
* `TEST_NAMESPACE` - String. Namespace in which testing needs to be done.
* `TEST_PHASES` - String. Comma separated string containing list of phases. Valid phases are LOAD, RUN and DELETE. Example: LOAD,DELETE

This should spin up a redis pod and a test orchestrator pod in your desired namespace and start running the tests. Tail the pod logs for more info.

### More about tests

The tests use [Vegeta](https://github.com/tsenart/vegeta) to trigger the load and index the results to specified elastic search instance. The list of apis involved in each phase as as below:

### LOAD PHASE 														
> **NOTE**: n is number of objects/requests here
#### APIs with O(n) operations
POST /api/v1/superuser/users # create_users method  
PUT /api/v1/superuser/users # update_passwords method  
POST /api/v1/repository # create_repositories method  
PUT /api/v1/repository/test # update_repositories method  
PUT /api/v1/organization/test/team # create_teams method

#### APIs with O(n^2) operations
PUT /api/v1/organization/test/team/team_1/members/member_1 # add_team_members method  
PUT /api/v1/repository/test/repo_1/permissions/team/team_1 # add_teams_to_organization_repos  
PUT /api/v1/repository/test/repo_1/permissions/user/user_1 # add_users_to_organization_repos  

### RUN PHASE
> **NOTE**: n is number of objects/requests here
#### APIs with O(n) operations
GET /api/v1/superuser/users/user_1 # get_users method  
GET /api/v1/repository/test/repo_1 # get_repositories method  
GET /api/v1/organization/test/team/team_1/permissions # list_team_permissions method  
GET /api/v1/organization/test/team/team_1/members # list_team_members method  
GET /api/v1/repository/test/repo_1/permissions/team/ #list_teams_of_organization_repos  
GET /api/v1/repository/test/repo_1/permissions/user/ # list_users_of_organization_repos  
GET /v2/user_1/repo_1/tags/list # list_tags method  
GET /api/v1/superuser/users/ # list_users method  
GET /v2/_catalog # get_catalog method  

#### APIs with O(n^2) operations
GET /api/v1/repository/test/repo_1/permissions/team/team_1 # get_teams_of_organizations_repos method  
GET /api/v1/repository/test/repo_1/permissions/user/user_1 # get_users_of_organizations_repos method  

### Image push/pulls
Unfortunately we don’t have any APIs to hit at this moment. So those are tested using podman commands. For n objects we will be creating n jobs representing n users who will be uploading images in parallel with python multiprocessing implemented. Each job uploads and downloads specified number of images (i.e PUSH_PULL_NUMBERS which has default value of 50).

### DELETE PHASE  
> **NOTE**: n is number of objects/requests here
#### APIs with O(n) operations
DELETE /api/v1/organization/test/team/team_1 # delete_teams method  
DELETE /api/v1/repository/test/repo_1 # delete_repositories method  
DELETE /api/v1/superuser/users/user_1 # delete_users method  

#### APIs with O(n^2) operations
DELETE /api/v1/organization/test/team/team_1/members/member_1 # delete_team_members method  
DELETE /api/v1/repository/test/repo_1/permissions/team/team_1 # delete_teams_of_organizations_repos method  
DELETE /api/v1/repository/test/repo_1/permissions/user/user_1 # delete_users_of_organizations_repos method  
DELETE /api/v1/repository/test/repo_1/tag/tag_1 # delete_repository_tags method  

## **Profiling**
### **Application Level Profiling**
Inorder to perform application level profiling we use [pyroscope](https://pyroscope.io/docs/). To install pyroscope onto your cluster, deploy `assets/pyroscope-server.yaml`. Now wait until the pods are up and running in the `pyroscope` namespace. For other installation methods please refer [this](https://pyroscope.io/docs/server-install-macos/).   
Once pyroscope is ready, we should be able to logon to the pyroscope route in the `pyroscope` namespace and view the application level profiling data using the tags applied as filters. Please refer to this [tutorial](https://github.com/grafana/pyroscope/tree/main/examples/python/rideshare) and live [demo](https://demo.pyroscope.io/explore?query=rideshare-app-python.cpu%7B%7D&groupBy=region&groupByValue=All) for more details on integration.

### **System Level Profiling**
Inorder to perform system level profiling we use [parca](https://www.parca.dev/docs/overview). To install parca onto your cluster, deploy `assets/parca-server.yaml` and `assets/parca-agent.yaml` in sequence. Now wait until the pods are up and running in the `parca` namespace. For other installation method please refer [this](https://www.parca.dev/docs/quickstart).   
Once parca is ready, we should be able to logon to the parca route in the `parca` namespace and view the system level profiling data.

### **PostgresDB Profiling**
In order to perform low overhead database profiling we will be using [pgBadger](https://github.com/darold/pgbadger). Below are the steps to do profiling on postgresDB.

* **Step 1**: Login to the postgres DB and modify the postgres.conf in `/var/lib/pgsql/data/userdata/` with below flags (or can be modified according to our own use case).
```
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_error_verbosity = default
log_destination = 'stderr'
logging_collector = on
log_rotation_age = 1d
log_rotation_size = 0
log_truncate_on_rotation = on
log_min_duration_statement = 0
log_min_messages = debug1
```

* **Step 2**: Once after modifying the config restart the db using the below command
```
pg_ctl restart -D /var/lib/pgsql/data/userdata
```

* **Step 3**: Now we should be able to find the logs in `/var/lib/pgsql/data/userdata/log/`. Copy those logs to the location where `pgBadger` binary is installed.

* **Step 4**: Then execute the below command to process those logs and get an html report. For more details on usage of `pgBadger`, refer [here](https://github.com/darold/pgbadger#table-of-contents).
```
pgbadger -j 8 ~/output/postgresql-2023-06-18_141703.log -o /home/vchalla/output/output.html --format html
```

> **NOTE**: It is suggested to disable logs collector once we do the profiling to avoid overhead created by logs files getting accumulating in the DB.