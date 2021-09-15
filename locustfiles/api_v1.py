from locust import HttpUser, task, tag

from utils import *
import os

class QuayUser(HttpUser):

    def on_start(self):
        self.client.headers = {'Authorization': f'Bearer {os.environ["OAUTH_TOKEN"]}'}
        self.name = fetch_random_user()

    def on_stop(self):
        pass

    @task
    def discovery(self):
        """
            List all the API end points
        """
        path = '/api/v1/discovery'
        url = os.environ['QUAY_HOST'] + path
        self.client.get(url)

    @task
    def get_user_info(self):
        """
            Get user information for the authenticated user
        """
        path = '/api/v1/user/'
        url = os.environ['QUAY_HOST'] + path
        self.client.get(url)

    @task
    def create_user(self):
        """
            Post data to create new user
        """
        path = '/api/v1/user/'
        url = os.environ['QUAY_HOST'] + path
        data = {"username": self.name, "email": f"{self.name}@example.com", "password": "password"}
        self.client.post(url, json=data)

    # @trigger_event(request_type="delete", name="delete user")
    def delete_user(self):
        """
            Post data to delete created user: Cannot use: as deletes logged in user
        """
        path = '/api/v1/user/'
        url = os.environ['QUAY_HOST'] + path
        data = {"username": self.name, "email": f"{self.name}@example.com", "password": "password"}
        self.client.delete(url, json=data)

    @task
    def get_private_repos(self):
        """
            Get the available count of private repositories for the user
        """
        path = '/api/v1/user/private/'
        url = os.environ['QUAY_HOST'] + path
        self.client.get(url)
