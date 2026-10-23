"""Share the database-readiness hook with the direct WSGI start command."""
import os
from server_runtime import prepare_worker_database


def post_worker_init(worker):
    prepare_worker_database(os.environ.get('DATABASE_URL'))
