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