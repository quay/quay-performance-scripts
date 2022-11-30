from api import QuayUser
from skopeo_operations import SkopeoUser
from config import Settings

from urllib.parse import urlparse
from locust import events
import requests
import json


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--quay-oauth", type=str, env_var="QUAY_OAUTH_TOKEN", default="",
                        help="Quay TOKEN for authentication")
    parser.add_argument("--quay-username", type=str, env_var="QUAY_USERNAME", default="",
                        help="Quay username")
    parser.add_argument("--quay-password", type=str, env_var="QUAY_PASSWORD", default="",
                        help="Quay password")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    parsed_url = urlparse(environment.runner.environment.host)
    Settings.USER_INIT_METADATA["container_host"] = parsed_url.netloc.split('.')[1] if 'www' in parsed_url.netloc else \
        parsed_url.netloc
    if environment.parsed_options.quay_oauth:
        return

    url = environment.runner.environment.host + Settings.INITIALIZE_USER
    response = requests.post(url, json=Settings.USER_INIT_METADATA)
    if response.status_code != 200:
        print("Error initializing user")
        return

    # Initialize config vars
    content = json.loads(response.content)
    Settings.USER_INIT_METADATA["access_token_val"] = content["access_token"]


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if environment.parsed_options.quay_oauth:
        return
    url = environment.runner.environment.host + Settings.DELETE_USER
    # TODO: This does not work
    requests.delete(url, headers={"Authorization": f"Bearer {Settings.USER_INIT_METADATA['access_token_val']}"})
