import sys
import logging

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def print_header(title, **kwargs):
    """
    Pretty-Print a Banner.
    """
    metadata = " ".join(["%s=%s" % (k, v) for k, v in kwargs.items()])
    logging.info("%s\t%s", title, metadata)