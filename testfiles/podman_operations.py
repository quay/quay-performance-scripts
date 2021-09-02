from locust import User, task, tag
from subprocess import run

from config import Settings
from utils import trigger_event


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
        cmd = f"podman login {Settings.PODMAN_HOST} -u {Settings.PODMAN_USERNAME} -p {Settings.PODMAN_PASSWORD} --tls-verify=false"
        run(cmd, shell=True, capture_output=True)

        cmd = f"podman pull quay.io/alecmerdler/bad-image:critical --tls-verify=false"
        run(cmd, shell=True, capture_output=True)

        cmd= f"podman tag quay.io/alecmerdler/bad-image:critical {Settings.PODMAN_HOST}/admin/bad-image:critical"
        run(cmd, shell=True, capture_output=True)

        cmd = f"podman push {Settings.PODMAN_HOST}/admin/bad-image:critical --tls-verify=false"
        return run(cmd, shell=True, capture_output=True)
