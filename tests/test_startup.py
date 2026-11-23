"""Regression test: several gunicorn workers booting at once must not crash.

v2.0.0 first failed its container smoke test because two workers seeded the
admin user at the same moment and one died on the UNIQUE constraint.
"""

import multiprocessing as mp
import sqlite3

WORKERS = 6


def _boot(db_path, barrier, results):
    from app import create_app

    barrier.wait()  # release every "worker" at the same instant
    try:
        create_app(database=db_path)
        results.put("ok")
    except Exception as exc:  # pragma: no cover - only reached on regression
        results.put(repr(exc))


def test_concurrent_startup_on_fresh_database(tmp_path):
    db_path = str(tmp_path / "fresh.db")
    ctx = mp.get_context("spawn")
    barrier, results = ctx.Barrier(WORKERS), ctx.Queue()
    procs = [ctx.Process(target=_boot, args=(db_path, barrier, results)) for _ in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)

    outcomes = [results.get(timeout=5) for _ in procs]
    assert outcomes == ["ok"] * WORKERS

    conn = sqlite3.connect(db_path)
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0]
    columns = {row[1] for row in conn.execute("PRAGMA table_info(clients)")}
    conn.close()
    assert admins == 1
    assert {"membership_status", "membership_end"} <= columns


def test_restart_is_idempotent(tmp_path):
    from app import create_app

    db_path = str(tmp_path / "again.db")
    create_app(database=db_path)
    create_app(database=db_path)  # second boot: no duplicate user, no duplicate column
