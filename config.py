class Settings(object):
    PODMAN_USERNAME = 'admin'
    PODMAN_PASSWORD = 'password'
    PODMAN_HOST = 'localhost:8080'
    QUAY_HOST = 'http://www.localhost:8080'

    # Auth tokens
    AUTH_TOKEN = '<auth-token>'
    ROBOT_AUTH_TOKEN = '<robot-auth-token>'

    # Url Paths
    V2_AUTH = '/v2/auth'
    V1_CREATE_ORG = '/api/v1/organization/'
    V1_CREATE_REPO = '/api/v1/repository'
