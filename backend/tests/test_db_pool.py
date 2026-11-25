"""store._cursor connection pool: reuse, cleanup on errors, dead-connection replacement, size cap."""
import threading
import time

import psycopg2
import pytest

import store


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, *a):
        if self.conn.dead:
            raise psycopg2.OperationalError("server closed the connection")
        self.conn.queries.append(sql)


class FakeConn:
    def __init__(self):
        self.closed = 0
        self.dead = False
        self.queries = []
        self.commits = self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        if self.dead:
            raise psycopg2.InterfaceError("connection already closed")
        self.rollbacks += 1

    def close(self):
        self.closed = 1


@pytest.fixture
def pool(monkeypatch):
    made = []

    def connect():
        c = FakeConn()
        made.append(c)
        return c

    monkeypatch.setattr(store, "_connect", connect)
    monkeypatch.setattr(store, "_idle", [])
    monkeypatch.setattr(store, "_pool_slots", threading.BoundedSemaphore(2))
    return made


def test_connection_is_reused(pool):
    for _ in range(3):
        with store._cursor() as cur:
            cur.execute("SELECT 1")
    assert len(pool) == 1 and pool[0].commits == 3


def test_query_error_rolls_back_and_keeps_connection(pool):
    with pytest.raises(ValueError):
        with store._cursor():
            raise ValueError("boom")
    assert pool[0].rollbacks == 1 and not pool[0].closed
    assert len(store._idle) == 1


def test_connection_error_discards_connection(pool):
    with pytest.raises(psycopg2.OperationalError):
        with store._cursor():
            raise psycopg2.OperationalError("ssl closed")
    assert pool[0].closed and store._idle == []


def test_dead_idle_connection_is_replaced(pool):
    with store._cursor() as cur:
        cur.execute("SELECT 1")
    pool[0].dead = True
    store._idle[:] = [(pool[0], time.monotonic() - store._IDLE_PING_SECONDS - 1)]
    with store._cursor() as cur:
        cur.execute("SELECT 2")
    assert pool[0].closed and len(pool) == 2 and pool[1].queries == ["SELECT 2"]


def test_recently_used_connection_is_not_pinged(pool):
    with store._cursor() as cur:
        cur.execute("SELECT 1")
    with store._cursor() as cur:
        cur.execute("SELECT 2")
    assert pool[0].queries == ["SELECT 1", "SELECT 2"]  # no extra SELECT 1 ping


def test_pool_caps_open_connections(pool, monkeypatch):
    monkeypatch.setattr(store, "_POOL_WAIT_SECONDS", 0.05)
    with store._cursor(), store._cursor():
        with pytest.raises(RuntimeError, match="busy"):
            with store._cursor():
                pass
    assert len(pool) == 2


def test_review_prompt_state_reads_dict_rows(monkeypatch):
    """store._cursor yields RealDictCursor rows; unpacking one gives its keys, not values."""
    from contextlib import contextmanager

    class Cur:
        def execute(self, *a):
            pass

        def fetchone(self):
            return {"status": "pending", "scans": 7}

    @contextmanager
    def fake_cursor():
        yield Cur()

    monkeypatch.setattr(store, "_cursor", fake_cursor)
    assert store.get_review_prompt_state("u1") == ("pending", 7)
