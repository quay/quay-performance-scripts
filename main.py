import datetime
import logging
import math
import time
import os
import platform
import sys
import json
import uuid
import hashlib
import multiprocessing as mp
from endpoints.users import Users
from endpoints.repositories import Repositories
from endpoints.teams import Teams
from endpoints.permissions import Permissions
from endpoints.tags import Tags
from config import Config
from utils.util import print_header
from urllib3.exceptions import InsecureRequestWarning
from statistics import mean
from subprocess import Popen, PIPE

import redis
import requests
import warnings

from elasticsearch import Elasticsearch, helpers
from kubernetes import client, config
from concurrent.futures import ThreadPoolExecutor, as_completed

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Used for executing tests across multiple pods
redis_client = redis.Redis(host='redis')


# Configure Logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,  # DEBUG to see HTTP attempts, INFO for progress
    format='%(asctime)s [%(levelname)s] %(message)s'
)

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


def build_push_delete_single_image(tag, custom_build_image, max_failures=3):
    """
    Build, push, and delete a single image in one flow.
    Returns statistics dict matching push_single_image format.
    """
    # Build
    unique_id = str(uuid.uuid4())
    dockerfile = (
        f"FROM {custom_build_image if custom_build_image != "" else 'quay.io/jitesoft/alpine'}\n"
        f"RUN echo {unique_id} > /tmp/key.txt"
    )

    build_cmd = [
        'podman',
        'build',
        '--tag', tag,
        '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
        '--storage-driver', 'overlay',
        '--no-cache',
        '-f', '-'
    ]

    p = Popen(build_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, errors = p.communicate(input=dockerfile.encode('ascii'))
    build_success = p.returncode == 0

    if not build_success:
        logging.error(f"Failed to build image {tag}")
        logging.error(output.decode())
        logging.error(errors.decode())
        return None

    # Push with retries
    failure_count = 0
    success_count = 0

    start_time = datetime.datetime.utcnow()
    
    while failure_count < max_failures:
        push_cmd = [
            'podman',
            'push',
            tag,
            '--tls-verify=false',
            '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
            '--storage-driver', 'overlay',
        ]

        p = Popen(push_cmd, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()

        success = p.returncode == 0
        if success:
            success_count += 1
            break
        else:
            failure_count += 1
            logging.info(f"Failed to push tag: {tag}")
            logging.info(f"STDOUT: {output.decode()}")
            logging.info(f"STDERR: {errors.decode()}")
            logging.info(f"Retrying {failure_count}/{max_failures}")

    end_time = datetime.datetime.utcnow()

    # Delete image (always attempt)
    delete_cmd = [
        'podman',
        'rmi',
        tag,
        '--force',
        '--storage-opt', 'overlay.mount_program=/usr/bin/fuse-overlayfs',
        '--storage-driver', 'overlay',
    ]

    p = Popen(delete_cmd, stdout=PIPE, stderr=PIPE)
    p.communicate()

    elapsed_time = (end_time - start_time).total_seconds()
    
    return {
        'tag': tag,
        'targets': "image_pushes",
        'elapsed_time': elapsed_time,
        'start_time': start_time,
        'end_time': end_time,
        'failure_count': failure_count,
        'success_count': success_count,
        'successful': success,
    }


def podman_create(tags, custom_build_image="", concurrency=4):
    """
    Build, push, and delete multiple images concurrently using Podman.
    Each image follows: build -> push -> delete in a single flow.
    """
    print_header("Running: Build, Push, and Delete images using Podman", quantity=len(tags))
    env_config = Config().get_config()

    # Process all images concurrently (build -> push -> delete)
    push_results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(build_push_delete_single_image, tag, custom_build_image): tag 
            for tag in tags
        }
        
        for n, future in enumerate(as_completed(futures)):
            result = future.result()
            
            # Only add successful results (build_push_delete returns None on build failure)
            if result is not None:
                # Add metadata
                result['uuid'] = env_config["test_uuid"]
                result['cluster_name'] = env_config["quay_host"]
                result['hostname'] = platform.node()
                push_results.append(result)
            
            if n % 10 == 0:
                logging.info(f"{n}/{len(tags)} images completed pushing")

    # Write results to Elasticsearch
    logging.info("Writing 'registry push' results to Elasticsearch")
    es = Elasticsearch([env_config["es_host"]], port=env_config["es_port"])
    docs = [{
        '_index': env_config["push_pull_es_index"],
        'type': '_doc',
        '_source': r
    } for r in push_results]
    helpers.bulk(es, docs)

    # Print summary
    elapsed_times = [r['elapsed_time'] for r in push_results]
    summary = {
        'durations': {
            'mean': mean(elapsed_times),
            'max': max(elapsed_times),
            'min': min(elapsed_times),
        },
        'pushes': {
            'total': len(push_results)
        }
    }
    logging.info('Podman-Push Summary')
    logging.info(json.dumps(summary, sort_keys=True, indent=2))


def get_auth_token(registry, repository, username=None, password=None):
    """
    Get authentication token from registry.
    """
    auth_url = f"https://{registry}/v2/auth?service={registry}&scope=repository:{repository}:pull"
    
    try:
        if username and password:
            response = requests.get(auth_url, auth=(username, password), verify=False)
        else:
            response = requests.get(auth_url, verify=False)
        
        response.raise_for_status()
        token = response.json().get('token')
        return token
    except Exception as e:
        logging.info(f"Failed to get auth token: {e}")
        return None


def get_image_manifest(registry, repository, tag, token):
    """
    Fetch the manifest for a given image tag.
    Returns manifest JSON and list of layer digests.
    """
    manifest_url = f"https://{registry}/v2/{repository}/manifests/{tag}"
    headers = {
        'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = requests.get(manifest_url, headers=headers, verify=False)
        logging.debug(f"Fetching manifest for {tag}, HTTP {response.status_code}")
        response.raise_for_status()
        manifest = response.json()
        
        # Extract layer digests
        layers = []
        if 'layers' in manifest:
            layers = [layer['digest'] for layer in manifest['layers']]
        elif 'fsLayers' in manifest:  # Older manifest format
            layers = [layer['blobSum'] for layer in manifest['fsLayers']]
        
        return layers
    except Exception as e:
        logging.error(f"Failed to get manifest for {tag}: {e}")
        return []


def fetch_layer_with_retries(registry, repository, digest, token, max_attempts=3):
    """
    Attempt to download a single layer up to max_attempts times.
    Returns True on success, False on permanent failure.
    """
    url = f"https://{registry}/v2/{repository}/blobs/{digest}"
    headers = {"Authorization": f"Bearer {token}"}
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            with requests.get(url, headers=headers, stream=True, verify=False) as r:
                logging.debug(f"Fetching layer {digest}, attempt {attempt}, HTTP {r.status_code}")
                r.raise_for_status()
                sha = hashlib.sha256()
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):  # 2MB chunks
                    if not chunk:
                        break
                    sha.update(chunk)  # simulate compute load
                _ = sha.digest()
            logging.info(f"Layer {digest} succeeded on attempt {attempt} (HTTP {r.status_code})")
            return True
        except Exception as e:
            logging.warning(f"Layer {digest} attempt {attempt} failed: {e}")
            if attempt >= max_attempts:
                logging.error(f"Layer {digest} failed after {max_attempts} attempts: {e}")
                return False


def pull_single_image_http(tag, username=None, password=None, max_failures=3):
    """
    Pull image layers over HTTP (no local storage) with per-layer retries.
    Returns a dict matching your ES schema.
    """
    # parse registry/repository:tag
    try:
        parts = tag.split('/', 1)
        registry = parts[0]
        repo_tag = parts[1]
        repository, image_tag = repo_tag.rsplit(':', 1)
    except Exception:
        logging.info(f"Malformed tag: {tag}")
        return None

    start_time = datetime.datetime.utcnow()

    # get token and manifest
    try:
        token = get_auth_token(registry, repository, username, password)
    except Exception as e:
        logging.info(f"Auth/token retrieval failed for {tag}: {e}")
        return {
            'tag': tag,
            'targets': "image_pulls",
            'elapsed_time': 0.0,
            'start_time': start_time,
            'end_time': datetime.datetime.utcnow(),
            'success_count': 0,
            'failure_count': 1,
            'successful': False,
        }

    digests = get_image_manifest(registry, repository, image_tag, token)
    if not digests:
        end_time = datetime.datetime.utcnow()
        elapsed_time = (end_time - start_time).total_seconds()
        return {
            'tag': tag,
            'targets': "image_pulls",
            'elapsed_time': elapsed_time,
            'start_time': start_time,
            'end_time': end_time,
            'success_count': 0,
            'failure_count': 1,
            'successful': False,
        }

    success_count = 0
    failure_count = 0

    # Submit layer fetch tasks (each task includes its own retry logic)
    with ThreadPoolExecutor(max_workers=6) as layer_pool:
        futures = {
            layer_pool.submit(fetch_layer_with_retries, registry, repository, d, token, max_failures): d
            for d in digests
        }
        for fut in as_completed(futures):
            ok = fut.result()
            if not ok:
                failure_count += 1

    if failure_count == 0:
        success_count = 1
    end_time = datetime.datetime.utcnow()
    elapsed_time = (end_time - start_time).total_seconds()

    return {
        'tag': tag,
        'targets': "image_pulls",
        'elapsed_time': elapsed_time,
        'start_time': start_time,
        'end_time': end_time,
        'success_count': success_count,
        'failure_count': failure_count,
        'successful': (success_count == len(digests)),
    }


def podman_pull(tags, concurrency, username=None, password=None):
    """
    Pull multiple images concurrently using HTTP layer fetches with retries,
    and write results to Elasticsearch using the same document format.
    """
    logging.info("Running: HTTP-based image pull for all tags")
    env_config = Config().get_config()

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(pull_single_image_http, tag, username, password): tag
            for tag in tags
        }
        for n, fut in enumerate(as_completed(futures)):
            result = fut.result()
            if result is None:
                continue

            # Add metadata consistent with previous schema
            result['uuid'] = env_config["test_uuid"]
            result['cluster_name'] = env_config["quay_host"]
            result['hostname'] = platform.node()

            results.append(result)

            if n % 10 == 0:
                logging.info(f"Pulling {n}/{len(tags)} images completed.")

    # Write results to Elasticsearch
    logging.info("Writing 'registry pull' results to Elasticsearch")
    es = Elasticsearch([env_config["es_host"]], port=env_config["es_port"])
    docs = [{
        '_index': env_config["push_pull_es_index"],
        'type': '_doc',
        '_source': r
    } for r in results]
    helpers.bulk(es, docs)

    # Summary logging (same fields as earlier)
    if results:
        elapsed_times = [r['elapsed_time'] for r in results]
        summary = {
            'durations': {
                'mean': mean(elapsed_times),
                'max': max(elapsed_times),
                'min': min(elapsed_times),
            },
            'pulls': {
                'total': len(results)
            }
        }
    else:
        summary = {'durations': {}, 'pulls': {'total': 0}}

    logging.info('HTTP-Pull Summary')
    logging.info(json.dumps(summary, sort_keys=True, indent=2))


def test_pull(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')
    concurrency = int(os.environ.get('CONCURRENCY'))

    assert username, 'Ensure QUAY_USERNAME is set on this job.'
    assert password, 'Ensure QUAY_PASSWORD is set on this job.'

    tags = []
    for n in range(num_tags):
        tag = redis_client.lpop('tags_to_pull'+"-".join(username.split("_")))
        if tag:
            tags.append(tag.decode('utf-8'))

    if tags:
        logging.info("Pulling %s tags", len(tags))
        podman_pull(tags, concurrency, username, password)
        logging.info("Finished pulling batch.")
    
    else:
        logging.info("No tags in pull queue. Finished.")


def test_push(num_tags):

    username = os.environ.get('QUAY_USERNAME')
    password = os.environ.get('QUAY_PASSWORD')
    concurrency = int(os.environ.get('CONCURRENCY'))
    custom_build_image = os.environ.get('CUSTOM_BUILD_IMAGE', '')

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
        podman_create(tags, custom_build_image, concurrency)
        logging.info("Finished pushing batch.")
    
    else:
        logging.info("No tags in build queue. Finished.")


def create_test_push_job(namespace, quay_host, username, password, concurrency,
                            test_uuid, token, batch_size, tag_count, image, 
                            custom_build_image, target_hit_size):
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
        client.V1EnvVar(name='CUSTOM_BUILD_IMAGE', value=custom_build_image),
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
            'cpu': '1m',
            'memory': '10Mi',
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
                            test_uuid, token, batch_size, tag_count, image,
                            target_hit_size):
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
            'cpu': '1m',
            'memory': '10Mi',
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
        metadata=client.V1ObjectMeta(labels={'quay-perf-test-component-pull': 'executor-'+"-".join(username.split("_"))}),
        spec=client.V1PodSpec(restart_policy='Never', containers=[container])
    )

    spec = client.V1JobSpec(template=template, backoff_limit=0,
                            parallelism=concurrency, completions=num_jobs, ttl_seconds_after_finished=120)

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test-registry-pull"+"-".join(username.split("_"))),
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
        common_args['batch_size'], len(common_args['tags']), common_args['push_pull_image'], common_args['custom_build_image'],
        common_args['target_hit_size'])
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
    create_test_pull_job(common_args['namespace'], common_args['quay_host'], user, common_args['password'], 
                         common_args['concurrency'], common_args['uuid'], common_args['auth_token'], 
                         common_args['batch_size'], len(common_args['tags']), common_args['push_pull_image'], 
                         common_args['target_hit_size'])
    time.sleep(60)  # Give the Job time to start
    while True:

        # Check Job Status
        job_name = 'test-registry-pull'+"-".join(user.split("_"))
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
    if env_config["tags"] is not None:
        explicit_tags = env_config["tags"].split(",")
    else:
        explicit_tags = []
    if len(explicit_tags) > 0:
        logging.info("explicit tags: %s", explicit_tags)
        for tag in explicit_tags:
            tags.append(tag)
    else:
        if env_config["skip_push"] == "true" and int(env_config["pull_layers"]) > 0 and env_config["pull_repo_prefix"] != "":
            for i in range(1, int(env_config["push_pull_numbers"]) + 1):
                tags.append('%s_layers_%s_tag_%s' % (env_config["pull_repo_prefix"], env_config["pull_layers"], i))
        else:
            for i, repo_size in enumerate(repo_sizes):
                repo = repos_with_data[i]
                repo_tags = [
                    '%s/%s/%s:%s' % (env_config["quay_host"], organization, repo, n)
                    for n in range(0, repo_size)
                ]
                tags.extend(repo_tags)

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
        test_phases=env_config['test_phases'],
        skip_push=env_config['skip_push'],
        pull_layers=env_config['pull_layers'],
        pull_repo_prefix=env_config['pull_repo_prefix'],
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
    "skip_push": env_config["skip_push"],
    "pull_layers": env_config["pull_layers"],
    "pull_repo_prefix": env_config["pull_repo_prefix"],
    "custom_build_image": env_config["custom_build_image"]
    }

    if ('push_pull' in phases_list):
        time.sleep(60)
        username = os.environ.get('QUAY_USERNAME')
        batch_args['password'] = os.environ.get('QUAY_PASSWORD')
        start_time = datetime.datetime.utcnow()
        logging.info(f"Starting image push/pulls (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
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
