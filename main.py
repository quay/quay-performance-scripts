import datetime
import logging
import math
import time
import os
import platform
import sys
import json
import uuid
import multiprocessing as mp
from endpoints.users import Users
from endpoints.repositories import Repositories
from endpoints.teams import Teams
from endpoints.permissions import Permissions
from endpoints.tags import Tags
from config import Config
from utils.attacker import Attacker
from utils.util import print_header

from statistics import mean
from subprocess import run, Popen, PIPE, STDOUT

import redis
import yaml

from elasticsearch import Elasticsearch, helpers
from kubernetes import client, config


# Used for executing tests across multiple pods
redis_client = redis.Redis(host='redis')


# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def podman_login(username, password):
    """
    Execute podman to login to the registry.
    """
    print_header("Running: Login with Podman", username=username, password=password)
    env_config = Config().get_config()

    cmd = [
        'podman',
        'login',
        '-u', username,
        '-p', password,
        '--tls-verify=false',
        '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
        '--storage-driver', 'overlay',
        env_config["quay_host"]
    ]
    p = Popen(cmd, stdout=PIPE)
    p.communicate()
    assert p.returncode == 0


def podman_create(tags):
    """
    Execute podman to build and push all tags from unique images.
    """
    print_header("Running: Build images using Podman", quantity=len(tags))
    env_config = Config().get_config()

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
            logging.error("Failed to build image.")
            logging.error(output)
            logging.error(errors)
            raise

        # Status Messages
        if n % 10 == 0:
            logging.info("%s/%s images completed building." % (n, len(tags)))

    # TODO: Separate this into its own function
    print_header("Running: Push images using Podman", quantity=len(tags))

    results = []
    for n, tag in enumerate(tags):

        # Give failures a few tries as this load test is not always performed
        # within production quality environments.
        failure_count = 0
        success_count = 0
        max_failures = 3

        while failure_count < max_failures:

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
                success_count = success_count + 1
            except Exception:
                success = False
                failure_count = failure_count + 1
                logging.info("Failed to push tag: %s" % tag)
                logging.info("STDOUT: %s" % output)
                logging.info("STDERR: %s" % errors)
                logging.info("Retrying. %s/%s failures." % (failure_count, max_failures))

            # Statistics / Data
            elapsed_time = end_time - start_time
            data = {
                'tag': tag,
                'targets': "image_pushes",
                'elapsed_time': elapsed_time.total_seconds(),
                'start_time': start_time,
                'end_time': end_time,
                'failure_count': failure_count,
                'success_count': success_count,
                'successful': success,
            }
            results.append(data)

            if success:
                break

        # Status Messages
        if n % 10 == 0:
            logging.info("Pushing %s/%s images completed." % (n, len(tags)))

    # Write data to Elasticsearch
    logging.info("Writing 'registry push' results to Elasticsearch")
    es = Elasticsearch([env_config["es_host"]], port=env_config["es_port"])
    docs = []
    for result in results:

        # Add metadata to the result
        result['uuid'] = env_config["test_uuid"]
        result['cluster_name'] = env_config["quay_host"]
        result['hostname'] = platform.node()

        # Create an Elasticsearch Doc
        doc = {
            '_index': env_config["push_pull_es_index"],
            'type': '_doc',
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
    logging.info('Podman-Push Summary')
    logging.info(json.dumps(data, sort_keys=True, indent=2))


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
    env_config = Config().get_config()

    results = []
    for n, tag in enumerate(tags):

        cmd = [
            'podman', 
            'pull', tag,
            '--tls-verify=false',
            '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
            '--storage-driver', 'overlay',
        ]

        failure_count = 0
        success_count = 0
        max_failures = 3

        while failure_count < max_failures:

            # Time the Push
            start_time = datetime.datetime.utcnow()
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            end_time = datetime.datetime.utcnow()

            # Handle Errors
            try:
                assert p.returncode == 0
                success = True
                success_count = success_count + 1
            except Exception:
                success = False
                failure_count = failure_count + 1
                logging.info("Failed to pull tag: %s" % tag)
                logging.info("STDOUT: %s" % output)
                logging.info("STDERR: %s" % errors)
                logging.info("Retrying. %s/%s failures." % (failure_count, max_failures))

            # Statistics / Data
            elapsed_time = end_time - start_time
            data = {
                'tag': tag,
                'targets': "image_pulls",
                'elapsed_time': elapsed_time.total_seconds(),
                'start_time': start_time,
                'end_time': end_time,
                'success_count': success_count,
                'failure_count': failure_count,
                'successful': success,
            }
            results.append(data)

            if success:
                break

        # Status Messages
        if n % 10 == 0:
            logging.info("Pulling %s/%s images completed." % (n, len(tags)))
            podman_clear_cache()

    # Write data to Elasticsearch
    logging.info("Writing 'registry pull' results to Elasticsearch")
    es = Elasticsearch([env_config["es_host"]], port=env_config["es_port"])
    docs = []
    for result in results:

        # Add metadata to the result
        result['uuid'] = env_config["test_uuid"]
        result['cluster_name'] = env_config["quay_host"]
        result['hostname'] = platform.node()

        # Create an Elasticsearch Doc
        doc = {
            '_index': env_config["push_pull_es_index"],
            'type': '_doc',
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
    logging.info('Podman-Pull Summary')
    logging.info(json.dumps(data, sort_keys=True, indent=2))


def test_pull(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')

    assert username, 'Ensure QUAY_USERNAME is set on this job.'
    assert password, 'Ensure QUAY_PASSWORD is set on this job.'

    tags = []
    for n in range(num_tags):
        tag = redis_client.lpop('tags_to_pull'+"-".join(username.split("_")))
        if tag:
            tags.append(tag.decode('utf-8'))

    if tags:
        podman_login(username, password)
        logging.info("Pulling %s tags", len(tags))
        podman_pull(tags)
        logging.info("Finished pulling batch.")
    
    else:
        logging.info("No tags in pull queue. Finished.")


def test_push(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')

    assert username, 'Ensure QUAY_USERNAME is set on this job.'
    assert password, 'Ensure QUAY_PASSWORD is set on this job.'

    tags = []
    for n in range(num_tags):
        tag = redis_client.lpop('tags_to_push'+"-".join(username.split("_")))
        if tag:
            tags.append(tag.decode('utf-8'))

    if tags:
        podman_login(username, password)
        logging.info("Creating and pushing %s tags", len(tags))
        podman_create(tags)
        logging.info("Finished pushing batch.")
    
    else:
        logging.info("No tags in build queue. Finished.")


def create_test_push_job(namespace, quay_host, username, password, concurrency,
                            test_uuid, token, batch_size, tag_count, image, target_hit_size):
    """
    Create a Kubernetes Job Batch where each job will pull <batch_size> items
    off the queue and perform the podman build + podman push action on them.
    """

    num_jobs = math.ceil(tag_count / batch_size)
    env_config = Config().get_config()

    env_vars = [
        client.V1EnvVar(name='QUAY_HOST', value=quay_host),
        client.V1EnvVar(name='PYTHONUNBUFFERED', value='0'),
        client.V1EnvVar(name='QUAY_USERNAME', value=username),
        client.V1EnvVar(name='QUAY_PASSWORD', value=password),
        client.V1EnvVar(name='CONCURRENCY', value=str(concurrency)),
        client.V1EnvVar(name='TARGET_HIT_SIZE', value=str(target_hit_size)),
        client.V1EnvVar(name='PUSH_PULL_IMAGE', value=image),
        client.V1EnvVar(name='PUSH_PULL_ES_INDEX', value=env_config["push_pull_es_index"]),
        client.V1EnvVar(name='PUSH_PULL_NUMBERS', value=str(env_config["push_pull_numbers"])),
        client.V1EnvVar(name='TEST_UUID', value=test_uuid),
        client.V1EnvVar(name='TEST_NAMESPACE', value=namespace),
        client.V1EnvVar(name='QUAY_OAUTH_TOKEN', value=token),
        client.V1EnvVar(name='QUAY_TEST_NAME', value='push'),
        client.V1EnvVar(name='QUAY_ORG', value=env_config["quay_org"]),
        client.V1EnvVar(name='TEST_BATCH_SIZE', value=str(batch_size)),
        client.V1EnvVar(name='ES_HOST', value=env_config["es_host"]),
        client.V1EnvVar(name='ES_PORT', value=str(env_config["es_port"])),
        client.V1EnvVar(name='ES_INDEX', value=env_config["es_index"]),
        client.V1EnvVar(name='TEST_PHASES', value=env_config["test_phases"]),
    ]

    resource_requirements = client.V1ResourceRequirements(
        requests={
            'cpu': '1',
            'memory': '512Mi',
        }
    )

    container = client.V1Container(
        name='python',
        image=image,
        security_context={'privileged': True},
        env=env_vars,
        resources=resource_requirements,
    )
        
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={'quay-perf-test-component-push': 'executor-'+"-".join(username.split("_"))}),
        spec=client.V1PodSpec(restart_policy='Never', containers=[container])
    )

    spec = client.V1JobSpec(template=template, backoff_limit=0,
                            parallelism=concurrency, completions=num_jobs, ttl_seconds_after_finished=120)

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test-registry-push"+"-".join(username.split("_"))),
        spec=spec
    )

    api = client.BatchV1Api()

    try:
        resp = api.create_namespaced_job(namespace=namespace, body=job)
    except Exception as e:
        logging.exception("Unable to create job: %s", str(e))
        logging.error(e.body)

    logging.info("Created Job: %s", resp.metadata.name)


def create_test_pull_job(namespace, quay_host, username, password, concurrency,
                            test_uuid, token, batch_size, tag_count, image, target_hit_size):
    """
    Create a Kubernetes Job Batch where each job will pull <batch_size> items
    off the queue and perform the podman pull action on them.
    """

    num_jobs = math.ceil(tag_count / batch_size)
    env_config = Config().get_config()

    env_vars = [
        client.V1EnvVar(name='QUAY_HOST', value=quay_host),
        client.V1EnvVar(name='PYTHONUNBUFFERED', value='0'),
        client.V1EnvVar(name='QUAY_USERNAME', value=username),
        client.V1EnvVar(name='QUAY_PASSWORD', value=password),
        client.V1EnvVar(name='CONCURRENCY', value=str(concurrency)),
        client.V1EnvVar(name='TARGET_HIT_SIZE', value=str(target_hit_size)),
        client.V1EnvVar(name='PUSH_PULL_IMAGE', value=image),
        client.V1EnvVar(name='PUSH_PULL_ES_INDEX', value=env_config["push_pull_es_index"]),
        client.V1EnvVar(name='PUSH_PULL_NUMBERS', value=str(env_config["push_pull_numbers"])),
        client.V1EnvVar(name='TEST_UUID', value=test_uuid),
        client.V1EnvVar(name='TEST_NAMESPACE', value=namespace),
        client.V1EnvVar(name='QUAY_OAUTH_TOKEN', value=token),
        client.V1EnvVar(name='QUAY_TEST_NAME', value='pull'),
        client.V1EnvVar(name='QUAY_ORG', value=env_config["quay_org"]),
        client.V1EnvVar(name='TEST_BATCH_SIZE', value=str(batch_size)),
        client.V1EnvVar(name='ES_HOST', value=env_config["es_host"]),
        client.V1EnvVar(name='ES_PORT', value=str(env_config["es_port"])),
        client.V1EnvVar(name='ES_INDEX', value=env_config["es_index"]),
        client.V1EnvVar(name='TEST_PHASES', value=env_config["test_phases"]),
    ]

    resource_requirements = client.V1ResourceRequirements(
        requests={
            'cpu': '1',
            'memory': '512Mi',
        }
    )

    container = client.V1Container(
        name='python',
        image=image,
        security_context={'privileged': True},
        env=env_vars,
        resources=resource_requirements,
    )
        
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={'quay-perf-test-component-pull': 'executor-'+"-".join(username.split("_")).replace("|","")}),
        spec=client.V1PodSpec(restart_policy='Never', containers=[container])
    )

    spec = client.V1JobSpec(template=template, backoff_limit=0,
                            parallelism=concurrency, completions=num_jobs, ttl_seconds_after_finished=120)

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test-registry-pull"+"-".join(username.split("_")).replace("|","")),
        spec=spec
    )

    api = client.BatchV1Api()

    try:
        resp = api.create_namespaced_job(namespace=namespace, body=job)
    except Exception as e:
        logging.exception("Unable to create job: %s", str(e))
        logging.error(e.body)

    logging.info("Created Job: %s", resp.metadata.name)


def parallel_process(user, **kwargs):
    """
    This function is triggered using python multiprocessing to create push/pull jobs in parallel
    with input concurrency specified. For example: If we input 10 users with concurrency 5, It will
    create 5 push/pull jobs first and 5 push/pull jobs next in batches to process them. It uses 
    redis to store all the tags to be pushed for each user by appending the unique username at 
    the end of the tag key which is used as an unique identifier to fetch all the tags to be uploaded 
    to that specific user's account.

    :param user: username
    :param kwargs: args required to create jobs
    :return: None
    """
    common_args = kwargs
    # Container Operations
    
    logging.info('*** parallel_process user: %s', user)
    
    redis_client.delete('tags_to_push'+"-".join(user.split("_")))  # avoid stale data
    redis_client.rpush('tags_to_push'+"-".join(user.split("_")), *common_args['tags'])
    logging.info('Queued %s tags to be created' % len(common_args['tags']))

    redis_client.delete('tags_to_pull'+"-".join(user.split("_")))  # avoid stale data
    redis_client.rpush('tags_to_pull'+"-".join(user.split("_")), *common_args['tags'])
    logging.info('Queued %s tags to be pulled' % len(common_args['tags']))

    # Start the Registry Push Test job
    if common_args['skip_push'] != "true":
        create_test_push_job(common_args['namespace'], common_args['quay_host'], user,
        common_args['password'], common_args['concurrency'], common_args['uuid'], common_args['auth_token'],
        common_args['batch_size'], len(common_args['tags']), common_args['push_pull_image'], common_args['target_hit_size'])
        time.sleep(60)  # Give the Job time to start
        while True:
            # Check Job Status
            job_name = 'test-registry-push'+"-".join(user.split("_"))
            job_api = client.BatchV1Api()
            resp = job_api.read_namespaced_job_status(name=job_name, namespace=common_args['namespace'])
            completion_time = resp.status.completion_time
            if completion_time:
                logging.info("Job %s has been completed." % (job_name))
                break

            # Log Queue Status
            remaining = redis_client.llen('tags_to_push'+"-".join(user.split("_")))
            logging.info('Waiting for %s to finish. Queue: %s/%s' % (job_name, remaining, len(common_args['tags'])))
            time.sleep(60 * 1)  # 1 minute

    # Start the Registry Pull Test job
    create_test_pull_job(common_args['namespace'], common_args['quay_host'], user, 
    common_args['password'], common_args['concurrency'], common_args['uuid'], common_args['auth_token'], 
    common_args['batch_size'], len(common_args['tags']), common_args['push_pull_image'], common_args['target_hit_size'])
    time.sleep(60)  # Give the Job time to start
    while True:

        # Check Job Status
        job_name = 'test-registry-pull'+"-".join(user.split("_")).replace("|","")
        job_api = client.BatchV1Api()
        resp = job_api.read_namespaced_job_status(name=job_name, namespace=common_args['namespace'])
        completion_time = resp.status.completion_time
        if completion_time:
            logging.info("Job %s has been completed." % (job_name))
            break

        # Log Queue Status
        remaining = redis_client.llen('tags_to_pull'+"-".join(user.split("_")))
        logging.info('Waiting for %s to finish. Queue: %s/%s' % (job_name, remaining, len(common_args['tags'])))
        time.sleep(60 * 1)  # 1 minute


def batch_process(users_chunk, batch_args):
    jobs = []
    for each_user in users_chunk:
        process = mp.Process(target=parallel_process, args=(each_user,), kwargs=batch_args)
        jobs.append(process)
        process.start()

    for proc in jobs:
        proc.join()


if __name__ == '__main__':

    config.load_incluster_config()
    if os.environ.get('TEST_UUID') is None:
        os.environ['TEST_UUID'] = str(uuid.uuid4())
    env_config = Config().get_config()
    phases = env_config['test_phases'].split(",") if env_config['test_phases'] else []
    phases_list = [item.lower() for item in phases]
    # Generate a new prefix for user, repository, and team names on each run.
    # This is to avoid name collisions in the case of a re-run.
    PREFIX = env_config["test_uuid"][-4:]

    # Avoid p_thread exception in currently used Dockerfile base image
    # TODO: Remove this when Alpine + Podman is fixed to avoid leaving
    #       fuse-overlayfs processses around, or when the base image is changed.
    if env_config["batch_size"] > 400:
        raise Exception("Max BATCH_SIZE is 400. Given: {}", env_config["batch_size"])

    # Ensure a directory exists for writing test results
    if not os.path.isdir(env_config["log_directory"]):
        os.mkdir(env_config["log_directory"])

    # Execute only the registry push tests
    if os.environ.get("QUAY_TEST_NAME") == 'push':
        test_push(env_config["batch_size"])
        exit(0)
    
    # Execute only the registry pull tests
    # TODO: Pulls don't suffer from the same problem as builds with the Alpine+Podman
    #       image. Just spin up n=CONCURRENCY workers and let them continuously
    #       pop tags off the queue and pull them from the registry.
    if os.environ.get("QUAY_TEST_NAME") == 'pull':
        test_pull(env_config["batch_size"])
        exit(0)

    organization = env_config["quay_org"]  # Organization/Namespace used for performance tests
    password = 'password'  # Password used for all created Users

    num_users = env_config["target_hit_size"]
    num_repos = env_config["target_hit_size"]
    num_teams = env_config["target_hit_size"]

    users = ['%s_user_%s' % (PREFIX, n) for n in range(0, num_users)]
    teams = ['%s_team_%s' % (PREFIX, n) for n in range(0, num_teams)]
    repos = ['%s_repo_%s' % (PREFIX, n) for n in range(0, num_repos)]

    # Create repositories which will contain a specified number of tags when the
    # registry operation tests are performed.
    repo_sizes = (env_config["push_pull_numbers"],)
    repos_with_data = ['repo_with_%s_tags' % n for n in repo_sizes]
    repos.extend(repos_with_data)  # Create these while running tests

    # Calculate all tags to be pushed/pulled
    tags = []
    for i, repo_size in enumerate(repo_sizes):
        repo = repos_with_data[i]
        repo_tags = [
            '%s/%s/%s:%s' % (env_config["quay_host"], organization, repo, n)
            for n in range(0, repo_size)
        ]
        tags.extend(repo_tags)

    explicit_tags = env_config["tags"].split(",")
    if len(explicit_tags) > 0:
        tags = []
        logging.info("explicit tags: %s", explicit_tags)
        for i in range(5000):
            for tag in explicit_tags:
                tags.append(tag)
    logging.info("final tags num: %s", len(tags))
    
    print_header(
        'Running Quay Scale & Performance Tests',
        date=datetime.datetime.utcnow().isoformat(),
        host=env_config["base_url"],
        test_uuid=env_config["test_uuid"],
        organization=organization,
        num_users=num_users,
        num_repos=len(repos),
        num_teams=num_teams,
        target_hit_size=env_config["target_hit_size"],
        concurrency=env_config["concurrency"],
        repos_with_tags_sizes=repo_sizes,
        total_tags=len(tags),
        pull_push_batch_size=env_config["batch_size"],
    )

    namespace = env_config["test_namespace"]

    if not ({'load', 'run', 'delete', 'push_pull'} & set(phases_list)):
        logging.info("No valid phases defined to run the tests. Valid options: LOAD, RUN, PUSH_PULL and DELETE")
        sys.exit()
    
    batch_args = {
    "namespace": namespace,
    "quay_host": env_config["quay_host"],
    "concurrency": env_config["concurrency"],
    "uuid": env_config["test_uuid"],
    "auth_token": env_config["auth_token"],
    "batch_size": env_config["batch_size"],
    "tags": tags,
    "push_pull_image": env_config["push_pull_image"],
    "target_hit_size": env_config["target_hit_size"],
    "skip_push": env_config["skip_push"]
    }

    if ('push_pull' in phases_list):
        time.sleep(60)
        username = os.environ.get('QUAY_USERNAME')
        batch_args['password'] = os.environ.get('QUAY_PASSWORD')
        start_time = datetime.datetime.utcnow()
        logging.info(f"Starting image push/pulls (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        logging.info("^^^PULL user: %s",[username])
        batch_process([username], batch_args)
        end_time = datetime.datetime.utcnow()
        logging.info(f"Ending image push/pulls (UTC): {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        exit(0)

    # Load Phase
    # These tests should run before container images are pushed
    start_time = datetime.datetime.utcnow()
    logging.info(f"Starting load phase (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    Users.create_users(env_config["base_url"], users)
    Users.update_passwords(env_config["base_url"], users, password)
    Repositories.create_repositories(env_config["base_url"], organization, repos)
    Repositories.update_repositories(env_config["base_url"], organization, repos)
    Teams.create_teams(env_config["base_url"], organization, teams)
    Teams.add_team_members(env_config["base_url"], organization, teams, users)
    Permissions.add_teams_to_organization_repos(env_config["base_url"], organization, repos, teams)
    Permissions.add_users_to_organization_repos(env_config["base_url"], organization, repos, users)
    end_time = datetime.datetime.utcnow()
    logging.info(f"Ending load phase (UTC): {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    elapsed_time = end_time - start_time
    logging.info(f"The load phase took {str(datetime.timedelta(seconds=elapsed_time.total_seconds()))}.")

    start_time = datetime.datetime.utcnow()
    logging.info(f"Starting image push/pulls (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    batch_args['password'] = password
    batch_process([users[0]], batch_args)
    end_time = datetime.datetime.utcnow()
    logging.info(f"Ending image push/pulls (UTC): {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    elapsed_time = end_time - start_time
    logging.info(f"The image push/pulls took {str(datetime.timedelta(seconds=elapsed_time.total_seconds()))}.")

    if ('run' not in phases_list):
        logging.info("Skipping run phase as it is not specified")
    else:
        # List/Run Phase
        # These tests should run *after* repositories contain images
        start_time = datetime.datetime.utcnow()
        logging.info(f"Starting run phase (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        Users.list_users(env_config['base_url'], env_config["target_hit_size"])
        Users.get_users(env_config['base_url'], users)
        Repositories.get_repositories(env_config['base_url'], organization, repos)
        Permissions.list_team_permissions(env_config['base_url'], organization, teams)
        Permissions.get_teams_of_organization_repos(env_config['base_url'], organization, repos, teams)
        Permissions.list_teams_of_organization_repos(env_config['base_url'], organization, repos)
        Permissions.get_users_of_organization_repos(env_config['base_url'], organization, repos, users)
        Permissions.list_users_of_organization_repos(env_config['base_url'], organization, repos)
        Tags.get_catalog(env_config['base_url'], env_config["target_hit_size"])
        Tags.list_tags(env_config['base_url'], env_config['quay_host'], [users[0]], "repo_with_" + str(env_config["push_pull_numbers"]) + "_tags")
        end_time = datetime.datetime.utcnow()
        logging.info(f"Ending run phase (UTC): {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        elapsed_time = end_time - start_time
        logging.info(f"The run phase took {str(datetime.timedelta(seconds=elapsed_time.total_seconds()))}.")

    if ('delete' not in phases_list):
        logging.info("Skipping delete phase as it is not specified")
    else:
        # Cleanup Phase
        # These tests are ran at the end to cleanup stuff
        start_time = datetime.datetime.utcnow()
        logging.info(f"Starting cleanup phase (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        Permissions.delete_teams_of_organization_repos(env_config['base_url'], organization, repos, teams)
        Permissions.delete_users_of_organization_repos(env_config['base_url'], organization, repos, users)
        Teams.delete_team_members(env_config['base_url'], organization, teams, users)
        Teams.delete_teams(env_config['base_url'], organization, teams)
        Tags.delete_repository_tags(env_config['base_url'], organization, "repo_with_" + str(env_config["push_pull_numbers"]) + "_tags", tags, env_config["target_hit_size"])
        Repositories.delete_repositories(env_config['base_url'], organization, repos)
        Users.delete_users(env_config['base_url'], users)
        end_time = datetime.datetime.utcnow()
        logging.info(f"Ending cleanup phase (UTC): {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        elapsed_time = end_time - start_time
        logging.info(f"The cleanup phase took {str(datetime.timedelta(seconds=elapsed_time.total_seconds()))}.")
