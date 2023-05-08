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