"""Bounded per-process PostgreSQL reuse with rollback before handing a connection back."""
import os
import threading
import time
from collections import OrderedDict
import psycopg2
from psycopg2.pool import ThreadedConnectionPool, PoolError
from psycopg2.extras import RealDictCursor

_pool = None
_identity = None
_lock = threading.Lock()
_checked = OrderedDict()
_check_lock = threading.Lock()
_available = threading.Condition()


class DatabaseBusy(psycopg2.OperationalError):
    pass


def checkout(pool, timeout=3):
    """Wait briefly for a returned lease instead of failing a request immediately."""
    deadline = time.monotonic()+timeout
    with _available:
        while True:
            try:
                return pool.getconn()
            except PoolError:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise DatabaseBusy('Database connections are busy.') from None
                _available.wait(min(remaining, .25))



def recently_checked(conn):
    with _check_lock:
        checked = _checked.get(conn)
    return checked is not None and time.monotonic() - checked < 5


def remember_check(conn):
    with _check_lock:
        _checked[conn] = time.monotonic()
        _checked.move_to_end(conn)
        while len(_checked) > 16:
            _checked.popitem(last=False)


class Lease:
    def __init__(self, pool, conn):
        self._pool, self._conn = pool, conn

    def __getattr__(self, name):
        if self._conn is None:
            raise psycopg2.InterfaceError('Connection is closed')
        return getattr(self._conn, name)

    @property
    def closed(self):
        return self._conn.closed if self._conn is not None else 1

    def __enter__(self):
        if self.closed:
            raise psycopg2.InterfaceError('Connection is closed')
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()

    def close(self):
        conn, self._conn = self._conn, None
        if conn is None:
            return
        broken = bool(conn.closed)
        try:
            if not broken:
                conn.rollback()
        except psycopg2.Error:
            broken = True
        finally:
            if broken:
                with _check_lock:
                    _checked.pop(conn, None)
            try:
                self._pool.putconn(conn, close=broken)
            finally:
                with _available:
                    _available.notify_all()


def connect(dsn):
    global _pool, _identity
    identity = (os.getpid(), dsn)
    with _lock:
        if _pool is None or _identity != identity:
            _pool = ThreadedConnectionPool(1, 8, dsn, connect_timeout=5, cursor_factory=RealDictCursor)
            _identity = identity
        pool = _pool
    conn = checkout(pool)
    try:
        # A small ping costs less than reconnecting over TLS. Replace stale
        # connections before application SQL; never replay a failed write.
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = None
            conn = checkout(pool)
        # Keep the initial/stale-connection check, but avoid two extra database
        # round trips on every checkout during a burst of authenticated requests.
        # This caches only transport health, never user/session authorization.
        if not recently_checked(conn):
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
            conn.rollback()
            remember_check(conn)
        return Lease(pool, conn)
    except psycopg2.Error:
        if conn is not None:
            with _check_lock:
                _checked.pop(conn, None)
            pool.putconn(conn, close=True)
        fresh = checkout(pool)
        return Lease(pool, fresh)
