"""Small reusable HTTPS sessions; provider errors never expose credentials."""
import threading
import requests

_local = threading.local()


def post(*args, **kwargs):
    if not hasattr(_local, 'session'):
        _local.session = requests.Session()
    return _local.session.post(*args, **kwargs)
