from locust import HttpUser, task, tag

from config import Settings
import os
import random

counter = 1


class QuayUser(HttpUser):

    def __init__(self, parent):
        super().__init__(parent)
        self.repo_name = 'repo'
        self.robo_name = 'perf-rob'
        self.robo_counter = 0
        self.team_name = 'perf-team'
        self.team_counter = 0
        self.oauth_token = self.environment.parsed_options.quay_oauth or Settings.USER_INIT_METADATA["access_token_val"]
        self.org_name = ''

    def on_start(self):
        # generating jwt auth token
        # self.jwt_token = None
        # params = {
        #     "account": 'admin',
        #     "service": "localhost:8080",
        #     "scope": []
        # }
        # url = os.environ['QUAY_HOST'] + Settings.V2_AUTH
        # r = self.client.get(url, json=params, headers={'Authorization': f'Basic {os.environ['ROBOT_AUTH_TOKEN']}'})
        # if r.status_code == 200:
        #     resp = json.loads(r.content)
        #     self.jwt_token = resp['token']

        global org_counter
        self.org_name = 'org' + str(Settings.ORG_COUNTER)

        Settings.ORG_COUNTER += 1
        # create org
        url = self.environment.host + Settings.V1_CREATE_ORG
        self.client.post(url, json={'name': self.org_name}, headers={"Authorization": f"Bearer {self.oauth_token}"},
                         name='create_org')

        # create repo
        url = self.environment.host + Settings.V1_CREATE_REPO
        data = {"namespace": self.org_name, "repository": self.repo_name, "visibility": "public", "description": "",
                "repo_kind": "image"}
        self.client.post(url, json=data, headers={"Authorization": f"Bearer {self.oauth_token}"}, name='create_repo')

    def on_stop(self):
        # delete repo
        path = f'/api/v1/repository/{self.org_name}/{self.repo_name}'
        url = self.environment.host + path
        self.client.delete(url, headers={"Authorization": f"Bearer {self.oauth_token}"}, name='delete_repo')

        # delete org
        path = f'/api/v1/organization/{self.org_name}'
        url = self.environment.host + path
        self.client.delete(url, headers={"Authorization": f"Bearer {self.oauth_token}"}, name='delete_org')

    @task
    def list_tags(self):
        """
            List all the repo tags
        """
        path = f'/v2/{self.org_name}/{self.repo_name}/tags/list'
        url = self.environment.host + path
        self.client.get(url, headers=None, name='list_tags')

    # @task
    # def v2_support_enabled(self):
    #     """
    #         Check the API version and return True if it is supported
    #     """
    #     # TODO: Fix this (Currently gives 401)
    #     path = '/v2/'
    #     url = os.environ['QUAY_HOST'] + path
    #     r = self.client.get(url, headers={'Authorization': f'Bearer {self.jwt_token}'}, name='v2_support_enabled')
    #     print(r.status_code, r.content)

    @task
    def v1_create_org_robot(self):
        """
            V1: Get all members of an org
        """
        path = f'/api/v1/organization/{self.org_name}/robots/{self.robo_name+str(self.robo_counter)}'
        url = self.environment.host + path
        self.client.put(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_create_org_robot')
        self.robo_counter += 1

    @task
    def v1_create_org_team(self):
        """
            V1: Get all members of an org
        """
        path = f'/api/v1/organization/{self.org_name}/team/{self.team_name+str(self.team_counter)}'
        url = self.environment.host + path
        self.client.put(url, json={"name": self.team_name, "role": "member"}, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_create_org_team')
        self.team_counter += 1

    @task
    def catalog_search(self):
        """
            Check the API version and return True if it is supported
        """
        path = '/v2/_catalog'
        url = self.environment.host + path
        self.client.get(url, name='catalog_search')

    @task
    def get_repository_images(self):
        """
            Build repository image response
        """
        path = f'/v1/repositories/{self.org_name}/{self.repo_name}/images'
        url = self.environment.host + path
        self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='get_repo_images')

    @task
    def v1_get_tags(self):
        """
            Build repository image response
        """
        path = f'/v1/repositories/{self.org_name}/{self.repo_name}/tags'
        url = self.environment.host + path
        self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_get_tags')

    @task
    def internal_ping(self):
        """
            Build repository image response
        """
        path = f'/v1/_internal_ping'
        url = self.environment.host + path
        self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='internal_ping')

    @task
    def v1_user(self):
        """
            V1: Get all users
        """
        path = f'/api/v1/user/'
        url = self.environment.host + path
        response = self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_user')

    @task
    def v2_user(self):
        """
            V1: Get all users
        """
        path = f'/api/v2_alpha/user/'
        url = self.environment.host + path
        response = self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v2_user')

    @task
    def v2_organization(self):
        """
            V1: Get all users
        """
        path = f'/api/v2_alpha/organization/?&sort_type=asc&per_page=100'
        url = self.environment.host + path
        response = self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v2_organization')

    @task
    def v1_org_members(self):
        """
            V1: Get all members of an org
        """
        path = f'/api/v1/organization/{self.org_name}/members'
        url = self.environment.host + path
        self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_org_members')


    @task
    def v1_org_robots(self):
        """
            V1: Get all robots of an org
        """
        path = f"/api/v1/organization/{self.org_name}/robots"
        url = self.environment.host + path
        self.client.get(url, headers={'Authorization': f'Bearer {self.oauth_token}'}, name='v1_org_robots')
