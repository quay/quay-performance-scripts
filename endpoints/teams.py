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

        :param quay_url: quay host base url
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
    def delete_teams(quay_url, org, teams):
        """
        Deletes the specified teams.

        :param quay_url: quay host base url
        :param org: test org to delete teams in
        :param teams: list of teams
        :return None
        """
        print_header("Running: Delete Teams")
        path = '/api/v1/organization/%s/team' % org
        base_url = quay_url + path
        reqs = []
        for team in teams:
            request = {
                'url': base_url + '/%s' % team,
                'method': 'DELETE',
            }
            reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_teams', reqs, target_name=target_name)

    @staticmethod
    def add_team_members(quay_url, org, teams, users):
        """
        Add every specified user to every specified team.

        :param quay_url: quay host base url
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
    
    @staticmethod
    def list_team_members(quay_url, org, teams):
        """
        list team members of every specified team.

        :param quay_url: quay host base url
        :param org: test org to list teams in
        :param teams: list of teams
        :return None
        """
        print_header("Running: List Users of Teams")
        path = '/api/v1/organization/%s/team' % org
        base_url = quay_url + path
        reqs = []
        for team in teams:
            url = base_url + '/%s/members' % (team)
            request = {
                'url': url,
                'method': 'GET'
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('list_team_members', reqs, target_name=target_name)
    
    @staticmethod
    def delete_team_members(quay_url, org, teams, users):
        """
        Delete every specified user to every specified team.

        :param quay_url: quay host base url
        :param org: test org to delete teams members in
        :param teams: list of teams
        :param users: list of users
        :return None
        """
        print_header("Running: Delete Users to Teams")
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
                    'method': 'DELETE'
                }
                reqs.append(request)
        target_name = "'DELETE %s'" % path
        Attacker().run_vegeta('delete_team_members', reqs, target_name=target_name)