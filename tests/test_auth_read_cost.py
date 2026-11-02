"""Fresh authentication needs one read, without an avoidable wire rollback."""
import db_pool
from test_core import backend


def test_lease_autocommit_controls_the_real_connection():
    class Connection:
        autocommit = False
    connection = Connection()
    lease = db_pool.Lease(None, connection)
    lease.autocommit = True
    assert connection.autocommit is True
    lease.autocommit = False
    assert connection.autocommit is False


def test_auth_read_avoids_rollback_round_trip_and_still_rechecks_session(backend, monkeypatch):
    traffic = {'reads': 0, 'wire_rollbacks': 0}
    class Connection:
        closed = False
        autocommit = False
        in_transaction = False
        def cursor(self): return Cursor(self)
        def rollback(self):
            traffic['wire_rollbacks'] += int(self.in_transaction)
            self.in_transaction = False
    class Cursor:
        def __init__(self, connection): self.connection = connection
        def execute(self, sql, args):
            assert 'session_version' in sql and args == (1,)
            traffic['reads'] += 1
            self.connection.in_transaction = not self.connection.autocommit
        def fetchone(self): return {'session_version': traffic['reads']}
        def close(self): pass
    class Pool:
        def putconn(self, connection, close=False): assert not connection.autocommit
    connection = Connection()
    monkeypatch.setattr(backend, 'get_db', lambda: db_pool.Lease(Pool(), connection))
    for expected in (1, None):
        with backend.app.test_request_context('/api/tasks'):
            backend.session.update(user_id=1, session_version=1)
            assert backend.require_user_id() == expected
    assert traffic == {'reads': 2, 'wire_rollbacks': 0}
