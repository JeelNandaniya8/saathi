"""Bounded per-process PostgreSQL reuse with rollback before handing a connection back."""
import os
import threading
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

_pool = None
_identity = None
_lock = threading.Lock()


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
            self._pool.putconn(conn, close=broken)


def connect(dsn):
    global _pool, _identity
    identity = (os.getpid(), dsn)
    with _lock:
        if _pool is None or _identity != identity:
            _pool = ThreadedConnectionPool(1, 8, dsn, connect_timeout=5, cursor_factory=RealDictCursor)
            _identity = identity
        pool = _pool
    conn = pool.getconn()
    try:
        # A small ping costs less than reconnecting over TLS. Replace stale
        # connections before application SQL; never replay a failed write.
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = None
            conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        conn.rollback()
        return Lease(pool, conn)
    except psycopg2.Error:
        if conn is not None:
            pool.putconn(conn, close=True)
        fresh = pool.getconn()
        return Lease(pool, fresh)
