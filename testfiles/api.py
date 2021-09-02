from locust import HttpUser, task, tag

from config import Settings

import json

counter = 1


class QuayUser(HttpUser):

    def __init__(self, parent):
        super().__init__(parent)
        self.repo_name = 'test_repo'
        self.robo_name = 'perf-robo'
        global counter
        self.org_name = 'test_org' + str(counter)
        counter += 1

    def on_start(self):
        # generating jwt auth token
        # self.jwt_token = None
        # params = {
        #     "account": 'admin',
        #     "service": "localhost:8080",
        #     "scope": []
        # }
        # url = Settings.QUAY_HOST + Settings.V2_AUTH
        # r = self.client.get(url, json=params, headers={'Authorization': f'Basic {Settings.ROBOT_AUTH_TOKEN}'})
        # if r.status_code == 200:
        #     resp = json.loads(r.content)
        #     self.jwt_token = resp['token']

        # create org
        url = Settings.QUAY_HOST + Settings.V1_CREATE_ORG
        self.client.post(url, json={'name': self.org_name}, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='create_org')

        # create repo
        url = Settings.QUAY_HOST + Settings.V1_CREATE_REPO
        data = {"namespace": self.org_name, "repository": self.repo_name, "visibility": "public", "description": "", "repo_kind": "image"}
        self.client.post(url, json=data, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='create_repo')

    def on_stop(self):
        # delete repo
        path = f'/api/v1/repository/{self.org_name}/{self.repo_name}'
        url = Settings.QUAY_HOST + path
        self.client.delete(url, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='delete_repo')

        # delete org
        path = f'/api/v1/organization/{self.org_name}'
        url = Settings.QUAY_HOST + path
        self.client.delete(url, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='delete_org')

    @task
    def list_tags(self):
        """
            List all the repo tags
        """
        path = f'/v2/{self.org_name}/{self.repo_name}/tags/list'
        url = Settings.QUAY_HOST + path
        self.client.get(url, headers=None, name='list_tags')

    # @task
    # def v2_support_enabled(self):
    #     """
    #         Check the API version and return True if it is supported
    #     """
    #     # TODO: Fix this (Currently gives 401)
    #     path = '/v2/'
    #     url = Settings.QUAY_HOST + path
    #     r = self.client.get(url, headers={'Authorization': f'Bearer {self.jwt_token}'}, name='v2_support_enabled')
    #     print(r.status_code, r.content)

    @task
    def catalog_search(self):
        """
            Check the API version and return True if it is supported
        """
        path = '/v2/_catalog'
        url = Settings.QUAY_HOST + path
        self.client.get(url, name='catalog_search')

    @task
    def get_repository_images(self):
        """
            Build repository image response
        """
        path = f'/v1/repositories/{self.org_name}/{self.repo_name}/images'
        url = Settings.QUAY_HOST + path
        self.client.get(url, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='get_repo_images')

    @task
    def v1_get_tags(self):
        """
            Build repository image response
        """
        path = f'/v1/repositories/{self.org_name}/{self.repo_name}/tags'
        url = Settings.QUAY_HOST + path
        self.client.get(url, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='v1_get_tags')

    @task
    def internal_ping(self):
        """
            Build repository image response
        """
        path = f'/v1/_internal_ping'
        url = Settings.QUAY_HOST + path
        self.client.get(url, headers={'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}, name='internal_ping')
