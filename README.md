# Quay Performance Tests

## Description

The purpose of this repository is to provide a set of scalability and
performance tests for Red Hat Quay and Project Quay. These tests are not
intended to necessarily push Quay to its limit but instead collect metrics on
various operations. These metrics are used to determine how changes to Quay
affects its performance. A side-effect of these tests is the ability to
identify bottlenecks and slow operations.

## Quickstart

The test suite is designed to run in-cluster and is fairly simple to start.
There are a few prerequisites and they will be explained below.

### Prerequisites

- Deploy a Kubernetes environment. The tests will run within the cluster.
- Deploy Quay, itself.
- In Quay, as a superuser (important), create an organization for testing
  purposes. Within that organization, create an application for testing
  purposes. Within that application, create an OAuth Token with all
  permissions (checkboxes) granted. Hold on to this token as it will be used
  later.

### Execution

The test suite will run as a collection of jobs within the Kubernetes cluster.
It is recommended to use a separate namespace for the tests.

In this repository, there is a Job YAML file which will deploy the performance
tests. This YAML file specifies some environment variables which should be
overridden for your specific environment. The deployment file also creates
a service account used for the Job(s) and deploys a Redis instance used as a
central queue.

1. Ensure the Job can run privileged. In Openshift, you may have to run
   `oc adm policy add-scc-to-user privileged system:serviceaccount:$NAMESPACE:default`
2. Edit the deployment file `deploy/test.job.yaml`
   1. Change `QUAY_HOST` to the value of your Quay deployment's URL. This
      should match the value of `SERVER_HOSTNAME` in Quay's `config.yaml`.
   2. Change `QUAY_OAUTH_TOKEN` to the value of the token you created for
      your application during the prerequisites.
   3. Change `QUAY_ORG` to the name of the organization you created during
      the prerequisites. Example: `test`.
   4. Change `ES_HOST` to the hostname of your Elasticsearch instance.
   5. Change `ES_PORT` to the port number your Elasticsearch instance is
      listening on.
3. Deploy the performance tests job: `kubectl create -f deploy/test.job.yaml -n $NAMESPACE`
   
At this point, a Job with a single pod should be running. The job will output
a decent amount of information to the logs if you'd like to watch its progress.
Eventually, the Job gets to a point where it will perform tests against the
registry aspects of the container (using podman) and will create other Jobs to
execute those operations.

## Environment Variables

The following environment variables can be specified in the Job's deployment
file to change the behavior of the tests.

| Key | Type | Required | Description |
| --- | ---- | :------: | ----------- |
| QUAY_HOST | string | y | hostname of Quay instance to test |
| QUAY_OAUTH_TOKEN | string | y | Quay Application OAuth Token. Used for authentication purposes on certain API endpoints. |
| QUAY_ORG | string | y | The organization which will contain all created resources during the tests. |
| ES_HOST | string | y | Hostname of the Elasticsearch instance used to store the test results. |
| ES_PORT | string | y | Port of the Elasticsearch instance used for storing test results. |
| BATCH_SIZE | string | n | Number of items to pop off the queue in each batch. This primarily applies to the registry push and pull tests. Do not exceed 400 until the known issue is resolved. |
| CONCURRENCY | int | n | Defaults to 4. The quantity of requests or test executions to perform in parallel. |

## Changelog

**v0.1.0**
changes:

- Tests are run using locust framework
- Concurrent testing is done using Locust in distributed mode
- Metrics are now exported as Prometheus metrics

**v0.0.2**

changes:

- Python is used for orchestrating and defining all tests.
- Tests now run within a kubernetes cluster.
- Registry tests are executed concurrently using parallel kubernetes jobs.
- Reduced the number of steps required to run the tests.

known issues:

- The orchestrator job does not cleanup the other jobs it creates. There is
  no owner attribute specified so they are not cleaned up when the main Job
  is deleted either.
- The image used for registry operations has an issue where `podman build`
  will leave fuse processes running after it has completed. This can cause a
  situation where all available threads are used. Due to this issue, the batch
  size for each Job in the "podman push" tests are limited to 400.
- The container image uses alpine:edge. This is the only version of Alpine which
  includes podman. Alpine was chosen as there are complications which arise from
  trying to perform build/push/pull operations within Kubernetes and Openshift.
  It seemed to eliminate some of those issues. Eventually, a stable image should
  be used instead.
- The output logging of some subprocesses is broken and creates very long lines.
- The primary Job does not watch for the failure of its child Jobs.

0.0.1

- The original implementation.
  
## Hacking on the Tests

(TODO) This section still needs to be written.

## Running tests using Locust

### Setup

The project expects the following environment variables:
- QUAY_USERNAME: Username to log into Podman
- QUAY_PASSWORD: Password for the above user
- QUAY_HOST: The url where Quay is hosted (Eg: http://localhost:8080)
- CONTAINER_HOST: The path where container images will be pushed to (Eg: localhost:8080)
- OAUTH_TOKENS: A list of authorization tokens to enable API calls(On Quay: Create an organization followed by creating an application in the organization. Generate token for the application. Eg: '["oauthtoken1", "oauthtoken2"]')
- CONTAINER_IMAGES: A list of container images with tag (if not defaults to latest tag) to run tests against. Eg: '["quay.io/prometheus/node-exporter:v1.2.2", "quay.io/bitnami/sealed-secrets-controller:v0.16.0"]')

### Building

From the main directory, the docker image can be built using the command: 

```bash
docker build -t perf-test -f Dockerfile-locust .
```

### Running

#### Locally for dev

```
docker run -e PODMAN_USERNAME="username" \
    -e PODMAN_PASSWORD="password" \
    -e PODMAN_HOST="localhost:8080" \
    -e QUAY_HOST="http://www.localhost:8080" \
    -e AUTH_TOKEN="abc" --privileged \
    -v /tmp/csivvv:/var/lib/containers \
    -p 8089:8089 --name quay-test -d perf-test`
```

Upon successful starting of the container, the locust dashboard is accessible
on port 8089.

The minimum number of users spawned to run the tests must be at least equal to
the number of users defined in `testfiles/run.py` to run all user classes.

#### Cluster

The tests are run via locust in distributed mode. There is a single master
which controls multiple worker pods. The number of replicas for the workers are
defined in `deploy/locust-distributed.yaml` file. 

Edit the `ConfigMap` `quay-locust-config` in the
`deploy/locust-distributed.yaml` and set the variables accordingly

Deploy locust on the cluster by running:

```
kubectl apply -f deploy/locust-distributed.yaml
```
