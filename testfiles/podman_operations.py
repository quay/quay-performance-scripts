from locust import HttpUser, User, task, tag
from subprocess import run

from utils import trigger_event
from config import Settings
import os
import random

counter = 1


class PodmanUser(HttpUser):

    def __init__(self, parent):
        super().__init__(parent)
        self.chosen_img = random.choice(Settings.CONTAINER_IMAGES)
        self.image_tag = 'latest'
        self.image_name = self.chosen_img
        if ':' in self.chosen_img:
            self.image_name, self.image_tag = self.chosen_img.split(':')[0].split('/')[-1], self.chosen_img.split(':')[-1]

        self.upstream_image = f"{os.environ['CONTAINER_IMAGE_HOST']}/{self.chosen_img}"
        global counter
        self.local_image = f"{os.environ['PODMAN_HOST']}/{os.environ['PODMAN_USERNAME']}/{self.image_name+str(counter)}:{self.image_tag}"
        counter += 1
        self.retries = 0

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
        try:
            cmd = f"podman login {os.environ['PODMAN_HOST']} -u {os.environ['PODMAN_USERNAME']} -p {os.environ['PODMAN_PASSWORD']} --tls-verify=false"
            run(cmd, shell=True, capture_output=True)

            while self.retries < Settings.MAX_PULL_RETRIES:
                cmd = f"podman pull {self.upstream_image} && \
                        podman tag {self.upstream_image} {self.local_image} && \
                        podman push {self.local_image} --tls-verify=false && \
                        podman rmi {self.upstream_image}"
                r = run(cmd, shell=True, capture_output=True)
                if r.returncode == 0:
                    break

                self.retries += 1
                continue

            self.retries = 0
            return r
        except RuntimeError:
            pass
        except Exception as err:
            return err
