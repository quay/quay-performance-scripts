from locust import events
import datetime


def trigger_event(**kwargs):
    def _trigger_event(func):
        def wrapper(self, *args):
            start_time = datetime.datetime.utcnow()
            response = func(self)
            end_time = datetime.datetime.utcnow()
            if response.returncode == 0:
                events.request_success.fire(
                    request_type=kwargs['request_type'],
                    name=kwargs['name'],
                    # converting to milliseconds
                    response_time=(end_time - start_time).total_seconds() * 1000,
                    response_length=0
                )
            else:
                events.request_failure.fire(
                    request_type=kwargs['request_type'],
                    name=kwargs['name'],
                    response_time=(end_time - start_time).total_seconds() * 1000,
                    exception=response.stderr,
                    response_length=0
                )

        return wrapper
    return _trigger_event
