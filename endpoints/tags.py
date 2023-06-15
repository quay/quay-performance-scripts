import json
import requests
from subprocess import run, Popen, PIPE, STDOUT
from utils.attacker import Attacker
from utils.util import print_header
from urllib3.exceptions import InsecureRequestWarning


class Tags:
    """
    Contains all the functions to interact with tags and catalog endpoints.
    """

    def __init__(self):
        pass

    @staticmethod
    def fetch_repo_tokens(quay_host, user, repo):
        """
        Fetches v2 token for a given repo of the user.
        
        :param quay_host: quay host name
        :param user: username
        :param repo: repository of a specified user
        :return: returns the token
        """
        url = f"https://{quay_host}/v2/auth?service={quay_host}&scope=repository:{user}/{repo}:pull,push"
        auth = (user, 'password')
        try:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            response = requests.get(url, auth=auth, verify=False)
            response.raise_for_status()
            command_output = response.json()
            return command_output.get('token', '')
        except requests.exceptions.RequestException as e:
            print("An error occurred during the request:", e)
            return ''

    @staticmethod
    def list_tags(quay_url, quay_host, users, repo):
        """
        List all tags for all given user repos.
        We query it on top of the tags created in the load phase.
        
        :param quay_url: quay host base url
        :param quay_host: quay host name
        :param users: list of usernames
        :param repo: repo to scan for tags
        :return: None
        """
        print_header('Listing tags for given users repos')
        test_name = 'list_tags_for_user_repos'

        reqs = []
        for user in users:
            path = '/v2/%s/%s/tags/list' % (user, repo)
            url = quay_url + path
            token = Tags.fetch_repo_tokens(quay_host, user, repo)
            headers = {
                "Content-Type": ["application/json"],
                "Authorization": [f"Bearer {token}"]
            }
            request = {
                "url": url,
                "method": "GET",
                "header": headers,
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta(test_name, reqs, target_name=target_name)

    @staticmethod
    def get_catalog(quay_url, target_hit_size):
        """
        Gets catalog specified number of times.

        :param quay_url: quay host base url
        :param target_hit_size: number of times to hit catalog endpoint
        :return: None
        """
        print_header("Running: Get Catalog")
        path = '/v2/_catalog'
        url = quay_url + path
        reqs = []
        for each in range(target_hit_size):
            request = {
                'header': None,
                'url': url,
                'method': 'GET',
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('get_catalog', reqs, target_name=target_name)

    @staticmethod
    def delete_repository_tags(quay_url, org, repo, tags, target_hit_size):
        """
        Deletes specified repository tags in the given organization.

        :param quay_url: quay host base url
        :param org: quay organization to test
        :param repo: repo name to delete tags in
        :param tags: list of tags to delete
        :param target_hit_size: hit size to generate those many requests
        :return: None
        """
        print_header("Running: Delete Repository Tags")
        path = '/api/v1/repository/%s/%s' % (org, repo)
        base_url = quay_url + path
        reqs = []
        for i in range(target_hit_size):
            for tag in tags:
                url = base_url + '/tag/%s' % (tag)
                request = {
                    'url': url,
                    'method': 'DELETE'
                }
                reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_repository_tags', reqs, target_name=target_name)