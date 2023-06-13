import os
import uuid


class Config:
    """
    Contains functions to get and set config.
    """
    def __init__(self):
        """
        Initializes the config.
        """
        self.config = dict()
    
    def get_config(self):
        """
        Sets the input config from ENVS.
        """
        self.config = {
            'log_directory': './logs',
            'protocol': 'https',
            'quay_host': os.environ.get("QUAY_HOST"),
            'quay_org': os.environ.get("QUAY_ORG"),
            'test_uuid': os.environ.get('TEST_UUID'),
            'auth_token': os.environ.get("QUAY_OAUTH_TOKEN"),
            'es_host': os.environ.get('ES_HOST'),
            'es_port': os.environ.get('ES_PORT'),
            'es_index': os.environ.get('ES_INDEX'),
            'push_pull_image': os.environ.get('PUSH_PULL_IMAGE'),
            'push_pull_es_index': os.environ.get('PUSH_PULL_ES_INDEX'),
            'push_pull_numbers': int(os.environ.get("PUSH_PULL_NUMBERS", 50)),
            'concurrency': int(os.environ.get("CONCURRENCY", 50)),
            'target_hit_size': int(os.environ.get('TARGET_HIT_SIZE')),
            'batch_size': int(os.environ.get('TEST_BATCH_SIZE', 400)),
            'test_namespace': os.environ.get("TEST_NAMESPACE"),
            'base_url': '%s://%s' % ("https", os.environ.get("QUAY_HOST")),
            'test_phases': os.environ.get('TEST_PHASES')
        }
        self.validate_config()
        return self.config
    
    def validate_config(self):
        """
        Validates the config.
        """
        assert self.config["quay_host"], "QUAY_HOST is not set"
        assert self.config["quay_org"], "QUAY_ORG is not set"
        assert self.config["test_uuid"], "TEST_UUID is not set"
        assert self.config["auth_token"], "AUTH_TOKEN is not set"
        assert self.config["es_host"], "ES_HOST is not set"
        assert self.config["es_port"], "ES_PORT is not set"
        assert self.config["es_index"], "ES_INDEX is not set"
        assert self.config["push_pull_image"], "PUSH_PULL_IMAGE is not set"
        assert self.config["push_pull_es_index"], "PUSH_PULL_INDEX is not set"
        assert self.config["push_pull_numbers"], "PUSH_PULL_NUMBERS is not set"
        assert isinstance(self.config["concurrency"], int), "CONCURRENCY is not an integer"
        assert self.config["target_hit_size"], "TARGET_HIT_SIZE is not set"
        assert isinstance(self.config["target_hit_size"], int), "TARGET_HIT_SIZE is not an integer"
        assert isinstance(self.config["batch_size"], int), "BATCH_SIZE is not an integer"
        assert self.config["test_namespace"], "TEST_NAMESPACE is not set"
        assert self.config["base_url"], "BASE_URL is not set"
        assert self.config["test_phases"], "TEST_PHASES are not set. Valid options are LOAD,RUN and DELETE"
