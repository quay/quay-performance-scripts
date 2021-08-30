from locust import HttpUser, task, tag

from config import Settings
from utils import *

import json

counter = 1

class QuayUser(HttpUser):

    def on_start(self):
        self.client.headers = {'Authorization': f'Bearer {Settings.AUTH_TOKEN}'}
        self.repo_name = 'test_repo'

        global counter
        self.org_name = 'test_org'+ str(counter)
        counter += 1

        # create org
        path = '/api/v1/organization/'
        url = Settings.QUAY_HOST + path
        self.client.post(url, json={'name': self.org_name})

        # create robot within organization
        path = f'/api/v1/organization/{self.org_name}/robots/perf-robo'
        url = Settings.QUAY_HOST + path
        r = self.client.put(url)
        print("Creating robot within org")
        print("status_code", r.status_code, "content", r.content)
        if r.status_code == 200:
            resp = json.loads(r.content)
            self.client.headers = {'Authorization': f'Bearer {resp["token"]}'}


        # check perms
        path = f'/api/v1/organization/{self.org_name}/robots/perf-robo/permissions'
        url = Settings.QUAY_HOST + path
        r = self.client.get(url)
        print("Checking robot permissions")
        print(r.status_code, r.content)

        # create repo
        path = '/api/v1/repository'
        url = Settings.QUAY_HOST + path
        data = {"namespace": self.org_name, "repository": self.repo_name, "visibility": "private", "description": "", "repo_kind": "image"}
        self.client.post(url, json=data)

    def on_stop(self):
        # delete repo
        path = f'/api/v1/repository/{self.org_name}/{self.repo_name}'
        url = Settings.QUAY_HOST + path
        self.client.delete(url)

        # delete org
        path = f'/api/v1/organization/{self.org_name}'
        url = Settings.QUAY_HOST + path
        self.client.delete(url)


    @task
    def list_tags(self):
        """
            List all the API end points
        """
        path = f'/v2/{self.org_name}/{self.repo_name}/tags/list'
        url = Settings.QUAY_HOST + path
        r = self.client.get(url)
        print("url", url)
        print("status code", r.status_code, "content", r.content)
