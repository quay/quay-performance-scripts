import os
import sys
import json
import base64
import logging
from config import Config
from subprocess import run, Popen, PIPE, STDOUT

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class Attacker:
    def __init__(self):
        pass

    def to_base64_json(self, obj):
        """
        Return a base64-encoded JSON string from a given Python object.
        """
        json_data = json.dumps(obj).encode('utf-8')
        string = base64.b64encode(json_data).decode('utf-8')
        return string

    def run_vegeta(self, test_name, request_dicts, target_name):
        """
        Run Vegeta to execute the given HTTP requests and output the statistics.

        target_name: A meaningful representation of what is being tested. Often,
                    this will be an API endpoint path.
        """
        logging.info("Preparing to execute %s HTTP Requests." % len(request_dicts))
        env_config = Config().get_config()

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
                req['body'] = self.to_base64_json(req_dict['body'])

            # Some tests do not need authentication. Allow them to pass `None`
            # as the request header to avoid injecting it.
            if 'header' not in req_dict:
                req['header'] = {
                    'Authorization': ['Bearer %s' % env_config["auth_token"]],
                    'Content-Type': ['application/json']
                }
            else:
                req['header'] = req_dict['header']

            req_string = json.dumps(req) + '\n'
            reqs = reqs + req_string

        # Sanity Checks
        assert reqs.strip()
        assert ' ' not in test_name

        # Ensure a directory exists for writing vegeta results
        if not os.path.isdir(env_config["log_directory"]):
            os.mkdir(env_config["log_directory"])

        # Run `vegeta attack` to execute the HTTP Requests
        cmd = [
            'vegeta', 'attack',
            '-lazy',
            '-format=json',
            '-rate', str(env_config["concurrency"]),
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
        result_filename = '%s/%s_%s_result.json' % (env_config["log_directory"], env_config["test_uuid"], test_name)
        cmd = ['vegeta', 'report', '--every=1s', '--type=json', '--output=%s' % result_filename]
        p = Popen(cmd, stdin=PIPE)
        p.communicate(input=output)
        assert p.returncode == 0
        logging.info('Results for test %s written to file: %s' % (test_name, result_filename))

        # Use Snafu to push results to Elasticsearch
        logging.info("Recording test results in ElasticSearch: %s", env_config["es_host"])
        cmd = [
            'run_snafu',
            '-t', 'vegeta',
            '-u', env_config["test_uuid"],
            '-w', str(env_config["concurrency"]),
            '-r', result_filename,
            # '--target_name', target_name,
            '--target_name', test_name,
        ]
        snafu_env = os.environ.copy()
        snafu_env['es'] = env_config["es_host"]
        snafu_env['es_port'] = env_config["es_port"]
        snafu_env['es_index'] = env_config["es_index"]
        snafu_env['clustername'] = env_config["quay_host"]
        p = Popen(cmd, stdout=PIPE, stderr=STDOUT, env=snafu_env)
        output, _ = p.communicate()
        logging.info(output)
        assert p.returncode == 0
