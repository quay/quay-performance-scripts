import json
import os


class Settings(object):
    # Url Paths
    V2_AUTH = '/v2/auth'
    V1_CREATE_ORG = '/api/v1/organization/'
    V1_CREATE_REPO = '/api/v1/repository'

    CONTAINER_IMAGES = json.loads(os.environ['CONTAINER_IMAGES'])
    OAUTH_TOKENS = json.loads(os.environ['OAUTH_TOKENS'])
