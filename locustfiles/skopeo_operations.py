from locust import User, task, tag
from subprocess import run

from utils import trigger_event
import os

class SkopeoUser(User):

    def on_start(self):
        pass

    @trigger_event(request_type="skopeo", name="Remove Images")
    def on_stop(self):
        """
            Clear all images from local cache
        """
        cmd = f"skopeo rmi --all --force"
        return run(cmd, shell=True, capture_output=True)

    @task
    @tag('skopeo_push_image')
    @trigger_event(request_type="skopeo", name="Image push")
    def push_image(self):
        """
            Pushing image via skopeo.
        """
        username = os.environ.get('QUAY_USERNAME', 'admin')
        password = os.environ['QUAY_PASSWORD']
        host = os.environ['QUAY_HOST']

        cmd = f"skopeo login -u {username} -p {password} --tls-verify=false {host} "
        run(cmd, shell=True, capture_output=True)

        cmd = ("skopeo copy --tls-verify=false"
                "docker://quay.io/alecmerdler/bad-image:critical"
                f"docker://{host}/{username}/bad-image:critial")
        run(cmd, shell=True, capture_output=True)
