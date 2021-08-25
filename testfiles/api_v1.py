from locust import HttpUser, task, tag
from subprocess import run

from config import Settings
from utils import *


class QuayUser(HttpUser):

    # @trigger_event(request_type="quay", name="setup")
    # def on_start(self):
    #     """
    #         Quay Setup
    #     """
    #
    #     return

    @task
    def create_user(self):
        """
            Create a Users in the test organization.
        """

        path = '/api/v1/discovery'
        url = Settings.QUAY_HOST + path
        print(url)
        name = fetch_user()
        resp = self.client.get(url, auth=None, headers={})
        print("response", resp)
        print("response content", resp.content)
