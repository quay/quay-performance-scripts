from locust import User, task, tag
from subprocess import run

from utils import trigger_event
from config import Settings
import os
import random


class SkopeoUser(User):

    def __init__(self, parent):
        super().__init__(parent)
        self.chosen_img = random.choice(Settings.CONTAINER_IMAGES)
        self.image_tag = 'latest'
        self.image_name = self.chosen_img
        if ':' in self.chosen_img:
            self.image_name, self.image_tag = self.chosen_img.split(':')[0].split('/')[-1], self.chosen_img.split(':')[-1]

        self.upstream_image = f"docker://{self.chosen_img}"
        self.local_image = f"docker://{os.environ['QUAY_HOST']}/{os.environ['PODMAN_USERNAME']}/{self.image_name}:{self.image_tag}"

    def on_start(self):
        username = os.environ.get('QUAY_USERNAME', 'admin')
        password = os.environ['QUAY_PASSWORD']
        host = os.environ['HOST']
        cmd = f"skopeo login -u {username} -p {password} --tls-verify=false {host}"
        run(cmd, shell=True, capture_output=True)

    def on_stop(self):
        pass

    @task
    @tag('skopeo_push_image')
    @trigger_event(request_type="skopeo", name="Image push")
    def push_image(self):
        """
            Pushing image via skopeo.
        """
        cmd = ("skopeo copy --dest-tls-verify=false "
                f"{self.upstream_image} {self.local_image}")
        return run(cmd, shell=True, capture_output=True)
