import json
from subprocess import run, Popen, PIPE, STDOUT
from utils.attacker import Attacker
from utils.util import print_header


class Tags:
    """
    Contains all the functions to interact with tags and catalog endpoints.
    """

    def __init__(self):
        pass

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