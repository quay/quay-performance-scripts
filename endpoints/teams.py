from utils.attacker import Attacker
from utils.util import print_header


class Teams:
    """
    Contains all the functions to interact with team endpoints.
    """
    def __init__(self):
        pass
    
    @staticmethod
    def create_teams(quay_url, org, teams):
        """
        Create the specified teams.

        :param org: test org to create teams in
        :param teams: list of teams
        :return None
        """
        print_header("Running: Create Teams")
        path = '/api/v1/organization/%s/team' % org
        base_url = quay_url + path
        reqs = []
        for team in teams:
            body = {'name': team, 'role': 'member'}
            request = {
                'body': body,
                'url': base_url + '/%s' % team,
                'method': 'PUT',
            }
            reqs.append(request)
        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('create_teams', reqs, target_name=target_name)

    @staticmethod
    def add_team_members(quay_url, org, teams, users):
        """
        Add every specified user to every specified team.

        :param org: test org to create teams in
        :param teams: list of teams
        :param users: list of users
        :return None
        """
        print_header("Running: Add Users to Teams")
        path = '/api/v1/organization/%s/team' % org
        base_url = quay_url + path
        reqs = []
        for team in teams:
            for user in users:
                url = base_url + '/%s/members/%s' % (team, user)
                body = {}  # No content
                request = {
                    'body': body,
                    'url': url,
                    'method': 'PUT'
                }
                reqs.append(request)
        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('add_team_members', reqs, target_name=target_name)