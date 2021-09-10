from locust import User, task, tag
from subprocess import run

from utils import trigger_event
import os

class PodmanUser(User):

    def on_start(self):
        pass

    @trigger_event(request_type="podman", name="Remove Images")
    def on_stop(self):
        """
            Clear all images from local cache
        """
        cmd = f"podman rmi --all --force"
        return run(cmd, shell=True, capture_output=True)

    @task
    @tag('podman_push_image')
    @trigger_event(request_type="podman", name="Image push")
    def push_image(self):
        """
            Pushing image via podman.
        """
        cmd = f"podman login {os.environ['PODMAN_HOST']} -u {os.environ['PODMAN_USERNAME']} -p {os.environ['PODMAN_PASSWORD']} --tls-verify=false"
        run(cmd, shell=True, capture_output=True)

        cmd = f"podman pull quay.io/alecmerdler/bad-image:critical --tls-verify=false"
        run(cmd, shell=True, capture_output=True)

        cmd= f"podman tag quay.io/alecmerdler/bad-image:critical {os.environ['PODMAN_HOST']}/admin/bad-image:critical"
        run(cmd, shell=True, capture_output=True)

        cmd = f"podman push {os.environ['PODMAN_HOST']}/admin/bad-image:critical --tls-verify=false"
        return run(cmd, shell=True, capture_output=True)
