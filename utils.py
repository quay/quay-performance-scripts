from locust import events
import datetime
import string
import random


def trigger_event(**kwargs):
    def _trigger_event(func):
        def wrapper(self, *args):
            start_time = datetime.datetime.utcnow()
            response = func(self)
            end_time = datetime.datetime.utcnow()
            if (kwargs['request_type'] == 'podman' and response.returncode == 0) or \
                    (kwargs['request_type'] != 'podman' and response.status_code == 200):
                events.request_success.fire(
                    request_type=kwargs['request_type'],
                    name=kwargs['name'],
                    # converting to milliseconds
                    response_time=(end_time - start_time).total_seconds() * 1000,
                    response_length=0
                )
            else:
                err = response.stderr if kwargs['request_type'] == 'podman' else response.content
                events.request_failure.fire(
                    request_type=kwargs['request_type'],
                    name=kwargs['name'],
                    response_time=(end_time - start_time).total_seconds() * 1000,
                    exception=err,
                    response_length=0
                )

        return wrapper
    return _trigger_event


def fetch_random_user():
    size = random.randint(4, 10)
    return ''.join(random.choices(string.ascii_lowercase, k=size))

