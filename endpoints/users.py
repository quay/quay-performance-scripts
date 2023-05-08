from utils.attacker import Attacker
from utils.util import print_header


class Users:
    """
    Contains all the functions to interact with user endpoints.
    """

    def __init__(self):
        pass
    
    @staticmethod
    def create_users(quay_url, usernames):
        """
        Create a series of Users within the test organization.

        :param quay_url: quay host base url
        :param usernames: list of usernames
        :return: None
        """
        print_header("Running: Create Users", quantity=len(usernames))
        path = '/api/v1/superuser/users'
        url = quay_url + path
        reqs = []
        for name in usernames:
            body = {'username': name, 'email': '%s@example.com' % name}
            request = {
                'body': body,
                'url': url,
                'method': 'POST'
            }
            reqs.append(request)
        target_name = "'POST %s'" % path
        Attacker().run_vegeta('create_users', reqs, target_name=target_name)

    @staticmethod
    def update_passwords(quay_url, usernames, password):
        """
        Set the password for the specified users.

        :param quay_url: quay host base url
        :param usernames: list of usernames
        :param password: password to be set for the users
        :return: None
        """
        print_header("Running: Update User Passwords", quantity=len(usernames))
        path = '/api/v1/superuser/users'
        url = quay_url + path
        reqs = []
        for user in usernames:
            body = {'password': 'password'}
            request = {
                'url': url + '/%s' % user,
                'body': body,
                'method': 'PUT'
            }
            reqs.append(request)
        target_name = "'PUT %s'" % path
        Attacker().run_vegeta('update_passwords', reqs, target_name=target_name)
    
    @staticmethod
    def list_users(quay_url, target_hit_size):
        """
        Lists a series of users within the test organization.

        :param quay_url: quay host base url
        :param target_hit_size: number of times to hit the endpoint
        :return: None
        """
        print_header("Running: List Users")
        path = '/api/v1/superuser/users/'
        url = quay_url + path
        requests = []
        for each in range(target_hit_size):
            request = {
                'url': url,
                'method': 'GET'
            }
            requests.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('list_users', requests, target_name=target_name)
    
    @staticmethod
    def get_users(quay_url, usernames):
        """
        Gets a series of Users within the test organization.

        :param quay_url: quay host base url
        :usernames: list of users to GET
        :return: None
        """
        print_header("Running: Get Users", quantity=len(usernames))
        path = '/api/v1/superuser/users'
        base_url = quay_url + path
        reqs = []
        for name in usernames:
            url = base_url + '/%s' % name
            request = {
                'url': url,
                'method': 'GET'
            }
            reqs.append(request)
        target_name = "'GET %s'" % path
        Attacker().run_vegeta('get_users', reqs, target_name=target_name)