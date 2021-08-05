from locust import User, task, tag
from subprocess import run

from config import Settings
from utils import trigger_event


class PodmanUser(User):

    @trigger_event(request_type="podman", name="Login")
    def on_start(self):
        """
            Login to podman
        """
        cmd = f"podman login localhost:8080 -u {Settings.PODMAN_USERNAME} -p {Settings.PODMAN_PASSWORD} --tls-verify=false"
        return run(cmd, shell=True, capture_output=True)

    @trigger_event(request_type="podman", name="Remove Images")
    def on_stop(self):
        """
            Clear all images from local cache
        """
        cmd = f"podman rmi --all --force"
        return run(cmd, shell=True, capture_output=True)

    @task
    @tag('podman_image_pull')
    @trigger_event(request_type="podman", name="Image pull")
    def pull_image(self):
        """
            Pulling an image via podman.
        """
        # TODO: Add logic to pull images from pool at random
        cmd = f"podman pull quay.io/alecmerdler/bad-image:critical --tls-verify=false"
        return run(cmd, shell=True, capture_output=True)

    @task
    @tag('podman_tag_image')
    @trigger_event(request_type="podman", name="Image tagging")
    def tag_image(self):
        """
            Tagging image via podman.
        """
        # TODO: Remove hardcoded image names by randomizing tagging
        cmd = f"podman tag quay.io/alecmerdler/bad-image:critical localhost:8080/admin/bad-image:critical"
        return run(cmd, shell=True, capture_output=True)

    @task
    @tag('podman_push_image')
    @trigger_event(request_type="podman", name="Image push")
    def push_image(self):
        """
            Pushing image via podman.
        """
        cmd = f"podman push localhost:8080/admin/bad-image:critical --tls-verify=false"
        return run(cmd, shell=True, capture_output=True)
