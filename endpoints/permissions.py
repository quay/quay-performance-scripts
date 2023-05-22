from utils.attacker import Attacker
from utils.util import print_header


class Permissions:
    """
    Contains all the functions to interact with permission endpoints.
    """
    def __init__(self):
        pass
    
    @staticmethod
    def add_teams_to_organization_repos(quay_url, org, repos, teams):
        """
        Give all specified teams access to all specified repos.

        :param quay_url: quay host base url
        :param org: test org to add teams to repos
        :param repos: repos in which teams need to be added
        :param teams: list of teams
        :return None
        """
        print_header("Running: Grant teams access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for team in teams:
                url = base_url + '/%s/permissions/team/%s' % (repo, team)
                body = {'role': 'admin'}
                request = {
                    'url': url,
                    'body': body,
                    'method': 'PUT',
                }
                reqs.append(request)
        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('add_teams_to_organizations', reqs, target_name=target_name)
    
    @staticmethod
    def add_users_to_organization_repos(quay_url, org, repos, users):
        """
        Give all specified users access to all specified repos.

        :param quay_url: quay host base url
        :param org: test org to add users to repos
        :param repos: repos in which users need to be added
        :param users: list of users
        :return None
        """
        print_header("Running: Grant users access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for user in users:
                url = base_url + '/%s/permissions/user/%s' % (repo, user)
                body = {'role': 'admin'}
                request = {
                    'url': url,
                    'body': body,
                    'method': 'PUT',
                }
                reqs.append(request)

        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('add_users_to_organizations_repos', reqs, target_name=target_name)
    
    @staticmethod
    def list_team_permissions(quay_url, org, teams):
        """
        list team org permissions of every specified team.

        :param quay_url: quay host base url
        :param org: test org to add users to repos
        :param teams: list of teams
        :return None
        """
        print_header("Running: List Permissions of Teams")
        path = '/api/v1/organization/%s/team' % org
        base_url = quay_url + path
        reqs = []
        for team in teams:
            url = base_url + '/%s/permissions' % (team)
            request = {
                'url': url,
                'method': 'GET'
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('list_team_permissions', reqs, target_name=target_name)

    @staticmethod
    def get_teams_of_organization_repos(quay_url, org, repos, teams):
        """
        Fetches the permission info of the specified team in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to list teams from
        :param repos: list of repos to scan
        :param teams: list of teams to GET
        :return: None
        """
        print_header("Running: Fetch teams access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for team in teams:
                url = base_url + '/%s/permissions/team/%s' % (repo, team)
                request = {
                    'url': url,
                    'method': 'GET',
                }
                reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('get_teams_of_organizations_repos', reqs, target_name=target_name)
    
    @staticmethod
    def list_teams_of_organization_repos(quay_url, org, repos):
        """
        Lists all teams permission info in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to list team permissions in
        :param repos: list of repos
        :return None
        """
        print_header("Running: Lists all teams access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            url = base_url + '/%s/permissions/team/' % (repo)
            request = {
                'url': url,
                'method': 'GET',
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('list_teams_of_organizations_repos', reqs, target_name=target_name)
    
    @staticmethod
    def get_users_of_organization_repos(quay_url, org, repos, users):
        """
        Fetches the permission of the specified user in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to list user permissions in
        :param repos: list of repos to scan
        :param users: list of users to fetch info
        :return None
        """
        print_header("Running: Fetch users access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for user in users:
                url = base_url + '/%s/permissions/user/%s' % (repo, user)
                request = {
                    'url': url,
                    'method': 'GET',
                }
                reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('get_users_of_organizations_repos', reqs, target_name=target_name)

    @staticmethod
    def list_users_of_organization_repos(quay_url, org, repos):
        """
        Lists all users permission info in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to list user permissions in
        :param repos: list of repos to scan
        :return None
        """
        print_header("Running: Lists all users access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            url = base_url + '/%s/permissions/user/' % (repo)
            request = {
                'url': url,
                'method': 'GET',
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('list_users_of_organizations_repos', reqs, target_name=target_name)
    
    @staticmethod
    def delete_teams_of_organization_repos(quay_url, org, repos, teams):
        """
        Deletes the permissions of the specified team in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to delete team permissions in
        :param repos: list of repos to scan
        :param teams: list of teams to delete
        :return None
        """
        print_header("Running: Delete teams access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for team in teams:
                url = base_url + '/%s/permissions/team/%s' % (repo, team)
                request = {
                    'url': url,
                    'method': 'DELETE',
                }
                reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_teams_of_organizations_repos', reqs, target_name=target_name)
    
    @staticmethod
    def delete_users_of_organization_repos(quay_url, org, repos, users):
        """
        Deletes the permissions of the specified user in all specified repos.

        :param quay_url: quay host base url
        :param org: test org to delete user permissions in
        :param repos: list of repos to scan
        :param users: list of users to delete
        :return None
        """
        print_header("Running: Delete users access to repositories")
        path = '/api/v1/repository/%s' % org
        base_url = quay_url + path
        reqs = []
        for repo in repos:
            for user in users:
                url = base_url + '/%s/permissions/user/%s' % (repo, user)
                request = {
                    'url': url,
                    'method': 'DELETE',
                }
                reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_users_of_organizations_repos', reqs, target_name=target_name)