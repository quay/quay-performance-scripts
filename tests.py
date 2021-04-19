import base64
import datetime
import json
import logging
import math
import time
import os
import platform
import sys
import uuid

from statistics import mean
from subprocess import run, Popen, PIPE, STDOUT

import redis
import yaml

from elasticsearch import Elasticsearch, helpers
from kubernetes import client, config


# Configuration Options
LOG_DIRECTORY = './logs'
PROTOCOL = 'https'  # TODO: Use environment variable
CONCURRENCY = 4


# In cases where only a single URL is hit, request it multiple times to get
# a somewhat reliable result.
DUPLICATE_REQUEST_COUNT = 1000


# Globals: ugly, but simplifies the rest of the code
QUAY_HOST = None
BASE_URL = None  # e.g. https://staging.quay.io
TEST_UUID = None
AUTH_TOKEN = None
ES_HOST = None
ES_PORT = None
ES_USER = 'elastic'
ES_PASSWORD = None
ES_INDEX = 'quay-vegeta'  # TODO: Use environment variable


# Used for executing tests across multiple pods
redis_client = redis.Redis(host='redis')


# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def to_base64_json(obj):
    """
    Return a base64-encoded JSON string from a given Python object.
    """
    json_data = json.dumps(obj).encode('utf-8')
    string = base64.b64encode(json_data).decode('utf-8')
    return string


def print_header(title, **kwargs):
    """
    Pretty-Print a Banner.
    """
    metadata = " ".join(["%s=%s" % (k, v) for k, v in kwargs.items()])
    logger.info("%s\t%s", title, metadata)


def run_vegeta(test_name, request_dicts, target_name):
    """
    Run Vegeta to execute the given HTTP requests and output the statistics.

    target_name: A meaningful representation of what is being tested. Often,
                 this will be an API endpoint path.
    """
    logger.info("Preparing to execute %s HTTP Requests." % len(request_dicts))

    # Convert request_dicts to a string and perform all needed transformations
    # for vegeta.
    reqs = ''
    for req_dict in request_dicts:

        req = {
            'url': req_dict['url'],
            'method': req_dict['method'],
        }

        # Do not send a body if the HTTP Method is GET. Otherwise, ensure
        # it's wrapped as a base64 encoded JSON string as expected by Vegeta.
        if 'body' in req_dict and req_dict['method'] != 'GET':
            req['body'] = to_base64_json(req_dict['body'])

        # Some tests do not need authentication. Allow them to pass `None`
        # as the request header to avoid injecting it.
        if 'header' not in req_dict or req_dict['header'] is not None:
            req['header'] = {
                'Authorization': ['Bearer %s' % AUTH_TOKEN],
                'Content-Type': ['application/json']
            }

        req_string = json.dumps(req) + '\n'
        reqs = reqs + req_string

    # Sanity Checks
    assert reqs.strip()
    assert ' ' not in test_name

    # Ensure a directory exists for writing vegeta results
    if not os.path.isdir(LOG_DIRECTORY):
        os.mkdir(LOG_DIRECTORY)

    # Run `vegeta attack` to execute the HTTP Requests
    cmd = [
        'vegeta', 'attack',
        '-lazy',
        '-format=json',
        '-rate', str(CONCURRENCY),
        '-insecure',
    ]
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    output, _ = p.communicate(input=reqs.encode('ascii'))

    # Show Vegeta Stats
    cmd = ['vegeta', 'report']
    p = Popen(cmd, stdin=PIPE)
    p.communicate(input=output)
    assert p.returncode == 0

    # Write Vegeta Stats to a file
    result_filename = '%s/%s_%s_result.json' % (LOG_DIRECTORY, TEST_UUID, test_name)
    cmd = ['vegeta', 'report', '--every=1s', '--type=json', '--output=%s' % result_filename]
    p = Popen(cmd, stdin=PIPE)
    p.communicate(input=output)
    assert p.returncode == 0
    logger.info('Results for test %s written to file: %s' % (test_name, result_filename))

    # Use Snafu to push results to Elasticsearch
    logger.info("Recording test results in ElasticSearch: %s", ES_HOST)
    cmd = [
        'run_snafu',
        '-t', 'vegeta',
        '-u', TEST_UUID,
        '-w', str(CONCURRENCY),
        '-r', result_filename,
        # '--target_name', target_name,
        '--target_name', test_name,
    ]
    snafu_env = os.environ.copy()
    snafu_env['es'] = ES_HOST
    snafu_env['es_port'] = ES_PORT
    snafu_env['es_index'] = ES_INDEX
    snafu_env['es_user'] = ES_USER
    snafu_env['es_password'] = ES_PASSWORD
    snafu_env['clustername'] = QUAY_HOST
    p = Popen(cmd, stdout=PIPE, stderr=STDOUT, env=snafu_env)
    output, _ = p.communicate()
    logger.info(output)
    assert p.returncode == 0


def create_users(usernames):
    """
    Create a series of Users within the test organization.
    """
    print_header("Running: Create Users", quantity=len(usernames))

    path = '/api/v1/superuser/users'
    url = BASE_URL + path

    reqs = []
    for name in usernames:
        body = {'username': name, 'email': '%s@example.com' % name}
        request = {
            'body': body,
            'url': url,
            'method': 'POST'
        }
        reqs.append(request)

    target_name = "'POST %s'" % path
    run_vegeta('create_users', reqs, target_name=target_name)


def update_passwords(usernames, password):
    """
    Set the password for the specified Users.
    """
    print_header("Running: Update User Passwords", quantity=len(usernames),
                 password=password)

    path = '/api/v1/superuser/users'
    url = BASE_URL + path

    reqs = []
    for user in usernames:

        body = {'password': password}
        request = {
            'url': url + '/%s' % user,
            'body': body,
            'method': 'PUT'
        }
        reqs.append(request)

    target_name = "'PUT %s'" % path
    run_vegeta('update_passwords', reqs, target_name=target_name)


def create_teams(org, teams):
    """
    Create the specified teams.
    """
    print_header("Running: Create Teams")

    path = '/api/v1/organization/%s/team' % org
    base_url = BASE_URL + path

    reqs = []
    for team in teams:
        body = {'name': team, 'role': 'member'}
        request = {
            'body': body,
            'url': base_url + '/%s' % team,
            'method': 'PUT',
        }
        reqs.append(request)
    
    target_name = "'PUT %s'" % path
    run_vegeta('create_teams', reqs, target_name=target_name)


def create_repositories(org, repos):
    """
    Create repositories in the specified organization.
    """
    print_header("Running: Create Repositories")

    path = '/api/v1/repository'
    url = BASE_URL + path

    reqs = []
    for repo in repos:

        body = {
            'description': 'performance tests',
            'repo_kind': 'image',
            'namespace': org,
            'repository': repo,
            'visibility': 'public',
        }

        request = {
            'body': body,
            'url': url,
            'method': 'POST'
        }

        reqs.append(request)

    target_name = "'POST %s'" % path
    run_vegeta('create_repositories', reqs, target_name=target_name)


def add_team_members(org, teams, users):
    """
    Add every specified user to every specified team.
    """
    print_header("Running: Add Users to Teams")

    path = '/api/v1/organization/%s/team' % org
    base_url = BASE_URL + path

    reqs = []
    for team in teams:
        for user in users:

            url = base_url + '/%s/members/%s' % (team, user)
            body = {}  # No content

            request = {
                'body': body,
                'url': url,
                'method': 'PUT'
            }

            reqs.append(request)

    target_name = "'PUT %s'" % path
    run_vegeta('add_team_members', reqs, target_name=target_name)


def add_teams_to_organization_repos(org, repos, teams):
    """
    Give all specified teams access to all specified repos.
    """
    print_header("Running: Grant teams access to repositories")

    path = '/api/v1/repository/%s' % org
    base_url = BASE_URL + path

    reqs = []
    for repo in repos:
        for team in teams:

            url = base_url + '/%s/permissions/team/%s' % (repo, team)
            body = {'role': 'admin'}

            request = {
                'url': url,
                'body': body,
                'method': 'PUT',
            }

            reqs.append(request)

    target_name = "'PUT %s'" % path
    run_vegeta('add_teams_to_organizations', reqs, target_name=target_name)


def get_catalog():
    """
    Fetch the v2 catalog
    
    Since this is only a single endpoint for each test run, we query it multiple
    times.
    """
    test_name = 'get_catalog'
    print_header("Running: %s" % test_name)

    path = '/v2/_catalog'
    url = BASE_URL + path

    reqs = []
    for _ in range(0, DUPLICATE_REQUEST_COUNT):
        request = {
            'method': 'GET',
            'url': url,
            'header': None,  # this endpoint throws 401s with the app token
        }
        reqs.append(request)

    target_name = "'GET %s'" % path
    run_vegeta(test_name, reqs, target_name=target_name)


def list_tags(org, repo):
    """
    List all tags for all given repositories.

    Since this is only a single endpoint for each test run, we query it multiple
    times.
    """
    print_header('List Tags', repository=repo)
    test_name = 'list_tags_for_%s' % repo

    path = '/v2/%s/%s/tags/list' % (org, repo)
    url = BASE_URL + path

    reqs = []
    for _ in range(0, DUPLICATE_REQUEST_COUNT):
        request = {
            'url': url,
            'method': 'GET',
            'header': None,  # this endpoint throws 401s with the app token
        }
        reqs.append(request)

    target_name = "'GET %s'" % path
    run_vegeta(test_name, reqs, target_name=target_name)


def podman_login(username, password):
    """
    Execute podman to login to the registry.
    """
    print_header("Running: Login with Podman", username=username, password=password)

    cmd = [
        'podman',
        'login',
        '-u', username,
        '-p', password,
        '--tls-verify=false',
        '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
        '--storage-driver', 'overlay',
        QUAY_HOST
    ]
    p = Popen(cmd, stdout=PIPE)
    p.communicate()
    assert p.returncode == 0


def podman_create(tags):
    """
    Execute podman to build and push all tags from unique images.
    """
    print_header("Running: Build images using Podman", quantity=len(tags))

    for n, tag in enumerate(tags):

        # Create a unique Dockerfile
        unique_id = str(uuid.uuid4())
        dockerfile = (
            "FROM quay.io/jitesoft/alpine\n"
            "RUN echo %s > /tmp/key.txt"
        ) % unique_id

        # Call Podman to build the Dockerfile
        cmd = [
            'podman',
            'build',
            '--tag', tag,
            '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
            '--storage-driver', 'overlay',
            '-f',
            '-'  # use stdin for Dockerfile content
        ]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate(input=dockerfile.encode('ascii'))
        try:
            assert p.returncode == 0
        except Exception:
            logger.error("Failed to build image.")
            logger.error(output)
            logger.error(errors)
            raise

        # Status Messages
        if n % 10 == 0:
            logger.info("%s/%s images completed building." % (n, len(tags)))

    # TODO: Separate this into its own function
    print_header("Running: Push images using Podman", quantity=len(tags))

    results = []
    for n, tag in enumerate(tags):

        # Give failures a few tries as this load test is not always performed
        # within production quality environments.
        failures = 0
        max_failures = 3

        while failures < max_failures:

            # Call Podman to push the Dockerfile
            cmd = [
                'podman',
                'push',
                tag,
                '--tls-verify=false',
                '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
                '--storage-driver', 'overlay',
            ]

            # Time the Push
            start_time = datetime.datetime.utcnow()
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            end_time = datetime.datetime.utcnow()

            # Handle Errors
            try:
                assert p.returncode == 0
                success = True
            except Exception:
                success = False
                failures = failures + 1
                logger.info("Failed to push tag: %s" % tag)
                logger.info("STDOUT: %s" % output)
                logger.info("STDERR: %s" % errors)
                logger.info("Retrying. %s/%s failures." % (failures, max_failures))

            # Statistics / Data
            elapsed_time = end_time - start_time
            data = {
                'tag': tag,
                'elapsed_time': elapsed_time.total_seconds(),
                'start_time': start_time,
                'end_time': end_time,
                'failures': failures,
                'successful': success,
            }
            results.append(data)

            if success:
                break

        # Status Messages
        if n % 10 == 0:
            logger.info("Pushing %s/%s images completed." % (n, len(tags)))

    # Write data to Elasticsearch
    logger.info("Writing 'registry push' results to Elasticsearch")
    es = Elasticsearch([ES_HOST], port=ES_PORT, http_auth=(ES_USER, ES_PASSWORD))
    index = 'quay-registry-push'
    docs = []
    for result in results:
        # Add metadata to the result
        result['uuid'] = TEST_UUID
        result['cluster_name'] = QUAY_HOST
        result['hostname'] = platform.node()

        # Create an Elasticsearch Doc
        doc = {
            '_index': index,
            '_type': '_doc',
            '_source': result
        }
        docs.append(doc)

    helpers.bulk(es, docs)  # bulk-push results to elasticsearch

    # Print some useful information
    elapsed_times = [result['elapsed_time'] for result in results]
    mean_elapsed_time = mean(elapsed_times)
    max_elapsed_time = max(elapsed_times)
    min_elapsed_time = min(elapsed_times)
    total_pushes = len(results)
    data = {
        'durations': {
            'mean': mean_elapsed_time,
            'max': max_elapsed_time,
            'min': min_elapsed_time,
        },
        'pushes': {
            'total': total_pushes
        }
    }
    logger.info('Podman-Push Summary')
    logger.info(json.dumps(data, sort_keys=True, indent=2))


def podman_clear_cache():
    """
    Execute podman to remove all created images from the local cache.

    TODO: Discard tags argument
    """
    cmd = [
        'podman',
        'rmi', '--all',
        '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
        '--storage-driver', 'overlay',
    ]
    p = Popen(cmd, stdout=PIPE)
    output, _ = p.communicate()
    assert p.returncode == 0


def podman_pull(tags):
    """
    Execute podman to pull all tags and collect relevant statistics.
    """
    print_header("Running: Podman Pull all tags")

    results = []
    for n, tag in enumerate(tags):

        cmd = [
            'podman', 
            'pull', tag,
            '--tls-verify=false',
            '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
            '--storage-driver', 'overlay',
        ]

        failures = 0
        max_failures = 3

        while failures < max_failures:
            # Time the Push
            start_time = datetime.datetime.utcnow()
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            end_time = datetime.datetime.utcnow()

            # Handle Errors
            try:
                assert p.returncode == 0
                success = True
            except Exception:
                success = False
                failures = failures + 1
                logger.info("Failed to pull tag: %s" % tag)
                logger.info("STDOUT: %s" % output)
                logger.info("STDERR: %s" % errors)
                logger.info("Retrying. %s/%s failures." % (failures, max_failures))

            # Statistics / Data
            elapsed_time = end_time - start_time
            data = {
                'tag': tag,
                'elapsed_time': elapsed_time.total_seconds(),
                'start_time': start_time,
                'end_time': end_time,
                'failures': failures,
                'successful': success,
            }
            results.append(data)

            if success:
                break

        # Status Messages
        if n % 10 == 0:
            logger.info("Pulling %s/%s images completed." % (n, len(tags)))
            podman_clear_cache()

    # Write data to Elasticsearch
    logger.info("Writing 'registry push' results to Elasticsearch")
    es = Elasticsearch([ES_HOST], port=ES_PORT)
    index = 'quay-registry-pull'
    docs = []
    for result in results:

        # Add metadata to the result
        result['uuid'] = TEST_UUID
        result['cluster_name'] = QUAY_HOST
        result['hostname'] = platform.node()

        # Create an Elasticsearch Doc
        doc = {
            '_index': index,
            '_type': '_doc',
            '_source': result
        }
        docs.append(doc)

    helpers.bulk(es, docs)  # bulk-push results to elasticsearch

    # Print some useful information
    elapsed_times = [result['elapsed_time'] for result in results]
    mean_elapsed_time = mean(elapsed_times)
    max_elapsed_time = max(elapsed_times)
    min_elapsed_time = min(elapsed_times)
    total_pushes = len(results)
    data = {
        'durations': {
            'mean': mean_elapsed_time,
            'max': max_elapsed_time,
            'min': min_elapsed_time,
        },
        'pushes': {
            'total': total_pushes
        }
    }
    logger.info('Podman-Pull Summary')
    logger.info(json.dumps(data, sort_keys=True, indent=2))


def test_pull(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')

    assert username, 'Ensure QUAY_USERNAME is set on this job.'
    assert password, 'Ensure QUAY_PASSWORD is set on this job.'

    tags = []
    for n in range(num_tags):
        tag = redis_client.lpop('tags_to_pull')
        if tag:
            tags.append(tag.decode('utf-8'))

    if tags:
        podman_login(username, password)
        logger.info("Pulling %s tags", len(tags))
        podman_pull(tags)
        logger.info("Finished pulling batch.")
    
    else:
        logger.info("No tags in pull queue. Finished.")


def test_push(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')

    assert username, 'Ensure QUAY_USERNAME is set on this job.'
    assert password, 'Ensure QUAY_PASSWORD is set on this job.'

    tags = []
    for n in range(num_tags):
        tag = redis_client.lpop('tags_to_push')
        if tag:
            tags.append(tag.decode('utf-8'))

    if tags:
        podman_login(username, password)
        logger.info("Creating and pushing %s tags", len(tags))
        podman_create(tags)
        logger.info("Finished pushing batch.")
    
    else:
        logger.info("No tags in build queue. Finished.")


def create_test_push_job(namespace, quay_host, username, password, concurrency,
                            test_uuid, token, batch_size, tag_count):
    """
    Create a Kubernetes Job Batch where each job will pull <batch_size> items
    off the queue and perform the podman build + podman push action on them.
    """

    num_jobs = math.ceil(tag_count / batch_size)

    env_vars = [
        client.V1EnvVar(name='QUAY_HOST', value=quay_host),
        client.V1EnvVar(name='PYTHONUNBUFFERED', value='0'),
        client.V1EnvVar(name='QUAY_USERNAME', value=username),
        client.V1EnvVar(name='QUAY_PASSWORD', value=password),
        client.V1EnvVar(name='CONCURRENCY', value=str(concurrency)),
        client.V1EnvVar(name='TEST_UUID', value=test_uuid),
        client.V1EnvVar(name='QUAY_OAUTH_TOKEN', value=token),
        client.V1EnvVar(name='QUAY_TEST_NAME', value='push'),
        client.V1EnvVar(name='QUAY_ORG', value=QUAY_ORG),
        client.V1EnvVar(name='TEST_BATCH_SIZE', value=str(batch_size)),
        client.V1EnvVar(name='ES_HOST', value=ES_HOST),
        client.V1EnvVar(name='ES_PORT', value=str(ES_PORT)),
    ]

    resource_requirements = client.V1ResourceRequirements(
        requests={
            'cpu': '1',
            'memory': '512Mi',
        }
    )

    container = client.V1Container(
        name='python',
        image='quay.io/kmullins/quay-performance-test:latest',
        security_context={'privileged': True},
        env=env_vars,
        resources=resource_requirements,
    )
        
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={'quay-perf-test-component': 'executor'}),
        spec=client.V1PodSpec(restart_policy='Never', containers=[container])
    )

    spec = client.V1JobSpec(template=template, backoff_limit=0,
                            parallelism=concurrency, completions=num_jobs)

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test-registry-push"),
        spec=spec
    )

    api = client.BatchV1Api()

    try:
        resp = api.create_namespaced_job(namespace=namespace, body=job)
    except Exception as e:
        logger.exception("Unable to create job: %s", str(e))
        logger.error(e.body)

    logger.info("Created Job: %s", resp.metadata.name)


def create_test_pull_job(namespace, quay_host, username, password, concurrency,
                            test_uuid, token, batch_size, tag_count):
    """
    Create a Kubernetes Job Batch where each job will pull <batch_size> items
    off the queue and perform the podman pull action on them.
    """

    num_jobs = math.ceil(tag_count / batch_size)

    env_vars = [
        client.V1EnvVar(name='QUAY_HOST', value=quay_host),
        client.V1EnvVar(name='PYTHONUNBUFFERED', value='0'),
        client.V1EnvVar(name='QUAY_USERNAME', value=username),
        client.V1EnvVar(name='QUAY_PASSWORD', value=password),
        client.V1EnvVar(name='CONCURRENCY', value=str(concurrency)),
        client.V1EnvVar(name='TEST_UUID', value=test_uuid),
        client.V1EnvVar(name='QUAY_OAUTH_TOKEN', value=token),
        client.V1EnvVar(name='QUAY_TEST_NAME', value='pull'),
        client.V1EnvVar(name='QUAY_ORG', value=QUAY_ORG),
        client.V1EnvVar(name='TEST_BATCH_SIZE', value=str(batch_size)),
        client.V1EnvVar(name='ES_HOST', value=ES_HOST),
        client.V1EnvVar(name='ES_PORT', value=str(ES_PORT)),
    ]

    resource_requirements = client.V1ResourceRequirements(
        requests={
            'cpu': '1',
            'memory': '512Mi',
        }
    )

    container = client.V1Container(
        name='python',
        image='quay.io/kmullins/quay-performance-test:latest',
        security_context={'privileged': True},
        env=env_vars,
        resources=resource_requirements,
    )
        
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={'quay-perf-test-component': 'executor'}),
        spec=client.V1PodSpec(restart_policy='Never', containers=[container])
    )

    spec = client.V1JobSpec(template=template, backoff_limit=0,
                            parallelism=concurrency, completions=num_jobs)

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test-registry-pull"),
        spec=spec
    )

    api = client.BatchV1Api()

    try:
        resp = api.create_namespaced_job(namespace=namespace, body=job)
    except Exception as e:
        logger.exception("Unable to create job: %s", str(e))
        logger.error(e.body)

    logger.info("Created Job: %s", resp.metadata.name)


if __name__ == '__main__':

    # Load Kubernetes configuration from the Cluster
    # NOTE: This will not work when running this script outside of k8s
    config.load_incluster_config()

    QUAY_HOST = os.environ.get("QUAY_HOST")
    AUTH_TOKEN = os.environ.get("QUAY_OAUTH_TOKEN")
    CONCURRENCY = os.environ.get("CONCURRENCY", 4)
    QUAY_ORG = os.environ.get("QUAY_ORG")

    TEST_UUID = os.environ.get('TEST_UUID', str(uuid.uuid4()))
    BASE_URL = '%s://%s' % (PROTOCOL, QUAY_HOST)

    ES_HOST = os.environ.get('ES_HOST')
    ES_PORT = os.environ.get('ES_PORT')

    # Generate a new prefix for user, repository, and team names on each run.
    # This is to avoid name collisions in the case of a re-run.
    PREFIX = TEST_UUID[-4:]

    # Quantity of container images to process in each individual job.
    BATCH_SIZE = int(os.environ.get('TEST_BATCH_SIZE', 400))

    # Sanity check configuration before starting tests
    assert QUAY_HOST
    assert BASE_URL
    assert TEST_UUID
    assert AUTH_TOKEN
    assert CONCURRENCY
    assert QUAY_ORG
    assert BATCH_SIZE
    assert isinstance(BATCH_SIZE, int)
    assert ES_HOST
    assert ES_PORT
    assert ES_INDEX

    # Avoid p_thread exception in currently used Dockerfile base image
    # TODO: Remove this when Alpine + Podman is fixed to avoid leaving
    #       fuse-overlayfs processses around, or when the base image is changed.
    if BATCH_SIZE > 400:
        raise Exception("Max BATCH_SIZE is 400. Given: {}", BATCH_SIZE)

    # Ensure a directory exists for writing test results
    if not os.path.isdir(LOG_DIRECTORY):
        os.mkdir(LOG_DIRECTORY)

    # Execute only the registry push tests
    if os.environ.get("QUAY_TEST_NAME") == 'push':
        test_push(BATCH_SIZE)
        exit(0)
    
    # Execute only the registry pull tests
    # TODO: Pulls don't suffer from the same problem as builds with the Alpine+Podman
    #       image. Just spin up n=CONCURRENCY workers and let them continuously
    #       pop tags off the queue and pull them from the registry.
    if os.environ.get("QUAY_TEST_NAME") == 'pull':
        test_pull(BATCH_SIZE)
        exit(0)

    organization = QUAY_ORG  # Organization/Namespace used for performance tests
    password = 'password'  # Password used for all created Users

    num_users = 100
    num_repos = 100
    num_teams = 10

    users = ['%s_user_%s' % (PREFIX, n) for n in range(0, num_users)]
    teams = ['%s_team_%s' % (PREFIX, n) for n in range(0, num_teams)]
    repos = ['%s_repo_%s' % (PREFIX, n) for n in range(0, num_repos)]

    # Create repositories which will contain a specified number of tags when the
    # registry operation tests are performed.
    repo_sizes = (1, 5, 10, 50, 100, 500, 1000, 5000)
    repos_with_data = ['repo_with_%s_tags' % n for n in repo_sizes]
    repos.extend(repos_with_data)  # Create these while running tests

    # Calculate all tags to be pushed/pulled
    tags = []
    for i, repo_size in enumerate(repo_sizes):
        repo = repos_with_data[i]
        repo_tags = [
            '%s/%s/%s:%s' % (QUAY_HOST, organization, repo, n)
            for n in range(0, repo_size)
        ]
        tags.extend(repo_tags)

    print_header(
        'Running Quay Scale & Performance Tests',
        date=datetime.datetime.utcnow().isoformat(),
        host=BASE_URL,
        test_uuid=TEST_UUID,
        organization=organization,
        num_users=num_users,
        num_repos=len(repos),
        num_teams=num_teams,
        concurrency=CONCURRENCY,
        repos_with_tags_sizes=repo_sizes,
    )

    # Get current namespace. Workaround for:
    # https://github.com/kubernetes-client/python/issues/363
    namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()

    # These tests should run before container images are pushed
    create_users(users)
    update_passwords(users, password)
    create_repositories(organization, repos)
    create_teams(organization, teams)
    add_team_members(organization, teams, users)
    add_teams_to_organization_repos(organization, repos, teams)

    # Container Operations
    redis_client.delete('tags_to_push')  # avoid stale data
    redis_client.rpush('tags_to_push', *tags)
    logger.info('Queued %s tags to be created' % len(tags))

    # Start the Registry Push Test job
    create_test_push_job(namespace, QUAY_HOST, users[0], password, CONCURRENCY, TEST_UUID, AUTH_TOKEN, BATCH_SIZE, len(tags))
    time.sleep(60)  # Give the Job time to start
    while True:

        # Check Job Status
        job_api = client.BatchV1Api()
        resp = job_api.read_namespaced_job_status(name='test-registry-push', namespace=namespace)
        completion_time = resp.status.completion_time
        if completion_time:
            logger.info("Job 'test-registry-push' completed.")
            break

        # Log Queue Status
        remaining = redis_client.llen('tags_to_push')
        logger.info('Waiting for "test-registry-push" to finish. Queue: %s/%s' % (remaining, len(tags)))
        time.sleep(60 * 5)  # 5 minutes

    redis_client.delete('tags_to_pull')  # avoid stale data
    redis_client.rpush('tags_to_pull', *tags)
    logger.info('Queued %s tags to be pulled' % len(tags))

    # Start the Registry Pull Test job
    create_test_pull_job(namespace, QUAY_HOST, users[0], password, CONCURRENCY, TEST_UUID, AUTH_TOKEN, BATCH_SIZE, len(tags))
    time.sleep(60)  # Give the Job time to start
    while True:

        # Check Job Status
        job_api = client.BatchV1Api()
        resp = job_api.read_namespaced_job_status(name='test-registry-pull', namespace=namespace)
        completion_time = resp.status.completion_time
        if completion_time:
            logger.info("Job 'test-registry-pull' completed.")
            break

        # Log Queue Status
        remaining = redis_client.llen('tags_to_pull')
        logger.info('Waiting for "test-registry-pull" to finish. Queue: %s/%s' % (remaining, len(tags)))
        time.sleep(60 * 5)  # 5 minutes

    # These tests should run *after* repositories contain images
    get_catalog()
    for repo in repos_with_data:
        list_tags(organization, repo)
