from utils.attacker import Attacker
from utils.util import print_header


class Repositories:
    """
    Contains all the functions to interact with repository endpoints.
    """

    def __init__(self):
        pass

    @staticmethod
    def create_repositories(quay_url, org, repos):
        """
        Create repositories in the specified organization.

        :param quay_url: quay host base url
        :param org: test org to create repositories in
        :param repos: list of repos to create
        :return: None
        """
        print_header("Running: Create Repositories")
        path = '/api/v1/repository'
        url = quay_url + path
        reqs = []
        for repo in repos:
            body = {
                'description': 'performance tests',
                'repo_kind': 'image',
                'namespace': org,
                'repository': repo,
                'visibility': 'public',
            }
            request = {
                'body': body,
                'url': url,
                'method': 'POST'
            }
            reqs.append(request)
        target_name = "'POST %s'" % path
        Attacker().run_vegeta('create_repositories', reqs, target_name=target_name)
    
    @staticmethod
    def update_repositories(quay_url, org, repos):
        """
        Update repositories in the specified organization.

        :param quay_url: quay host base url
        :param org: test org to update repositories in
        :param repos: list of repos to update
        :return: None
        """
        print_header("Running: Update Repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            url = base_url + '/%s' % (repo)
            body = {
                'description': 'new performance tests',
            }
            request = {
                'body': body,
                'url': url,
                'method': 'PUT'
            }
            reqs.append(request)
        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('update_repositories', reqs, target_name=target_name)
    
    @staticmethod
    def get_repositories(quay_url, org, repos):
        """
        Get specified repository in the given organization.

        :param quay_url: quay host base url
        :param org: test org to list repositories in
        :param repos: list of repos to GET
        :return: None
        """
        print_header("Running: Get Repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            url = base_url + '/%s' % (repo)
            request = {
                'url': url,
                'method': 'GET'
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('get_repositories', reqs, target_name=target_name)
    
    @staticmethod
    def delete_repositories(quay_url, org, repos):
        """
        Delete specified repository in the given organization.

        :param quay_url: quay host base url
        :param org: test org to list repositories in
        :param repos: list of repos to delete
        :return: None
        """
        print_header("Running: Delete Repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            url = base_url + '/%s' % (repo)
            request = {
                'url': url,
                'method': 'DELETE'
            }
            reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_repositories', reqs, target_name=target_name)