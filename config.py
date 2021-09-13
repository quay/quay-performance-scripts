import json
import os


class Settings(object):
    # Url Paths
    V2_AUTH = '/v2/auth'
    V1_CREATE_ORG = '/api/v1/organization/'
    V1_CREATE_REPO = '/api/v1/repository'

    CONTAINER_IMAGES = json.loads(os.environ['CONTAINER_IMAGES'])
    AUTH_TOKENS = json.loads(os.environ['AUTH_TOKENS'])
    MAX_PULL_RETRIES = 3
