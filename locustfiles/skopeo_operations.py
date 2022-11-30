from locust import User, task, tag
from subprocess import run

from utils import trigger_event
from config import Settings
import random


class SkopeoUser(User):

    def __init__(self, parent):
        super().__init__(parent)
        self.quay_username = self.environment.parsed_options.quay_username or Settings.USER_INIT_METADATA['username']
        self.quay_password = self.environment.parsed_options.quay_password or Settings.USER_INIT_METADATA['password']
        self.chosen_img = random.choice(Settings.CONTAINER_IMAGES)
        self.image_tag = 'latest'
        self.image_name = self.chosen_img
        self.image_name, self.image_tag = self.chosen_img.split(':')[0].split('/')[-1], self.chosen_img.split(':')[
            -1] if ':' in self.chosen_img else 'latest'

        self.upstream_image = f"docker://{self.chosen_img}" if ':' in self.chosen_img else f"docker://{self.chosen_img}:latest"
        self.local_image = f"docker://{Settings.USER_INIT_METADATA['container_host']}/" \
                           f"{self.quay_username}/{self.image_name}:{self.image_tag}"

    def on_start(self):
        cmd = f"skopeo login -u {self.quay_username} -p {self.quay_password} --tls-verify=false {self.environment.host}"
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
        cmd = ("skopeo --override-os linux copy --dest-tls-verify=false "
               f"{self.upstream_image} {self.local_image}")
        return run(cmd, shell=True, capture_output=True)
