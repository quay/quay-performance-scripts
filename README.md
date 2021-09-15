# Quay Performance Tests

## Description

The purpose of this repository is to provide a set of scalability and
performance tests for Red Hat Quay and Project Quay. These tests are not
intended to necessarily push Quay to its limit but instead collect metrics on
various operations. These metrics are used to determine how changes to Quay
affects its performance. A side-effect of these tests is the ability to
identify bottlenecks and slow operations.

## Quickstart

The test suite is designed to run both in-cluster and on local and is fairly simple to start.
There are a few prerequisites and they will be explained below.

### Prerequisites

- Deploy a Kubernetes environment. The tests will run within the cluster.
- Deploy Quay, itself.
- In Quay, as a superuser (important), create an organization for testing
  purposes. Within that organization, create an application for testing
  purposes. Within that application, create an OAuth Token with all
  permissions (checkboxes) granted. Hold on to this token as it will be used
  later.

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
- `QUAY_USERNAME`: Username to log into Podman
- `QUAY_PASSWORD`: Password for the above user
- `QUAY_HOST`: The url where Quay is hosted
- `OAUTH_TOKEN`: The Authorization Token to enable API calls(On Quay: Create an organization followed by creating an application in the organization. Generate token for the application.)

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
defined in `deploy/locust-distributed.yaml.example` file. 

Copy the `deploy/locust-distribyted.yaml.example` file to `deploy/locust-distributed.yaml`


```
cp deploy/locust-distribyted.yaml.example deploy/locust-distributed.yaml
```

1. Replace the placeholder `NAMESPACE` with your namespace
2. Edit the `ConfigMap` `quay-locust-config` in the `deploy/locust-distributed.yaml` and set the variables accordingly
3. If you want to use a different image update the `image` field in the master and worker deployment
4. Change the `replicas` field in the `worker` Deployment to the number you need (default is 2 workers)

Deploy locust on the cluster by running:

```
kubectl apply -f deploy/locust-distributed.yaml
```

This should deploy locust in distributed mode on the cluster. To access the web UI port-foward it locally

```
kubectl port-forward svc/locust-master -n <namespace> 8089
```
