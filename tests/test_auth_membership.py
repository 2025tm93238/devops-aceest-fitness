"""Tests for v2.0.0: role-based login and membership management."""

import sqlite3
from datetime import date, timedelta

import pytest

from app import create_app
from membership import membership_state, renewed_end

TODAY = date(2026, 11, 23)


@pytest.fixture
def admin_headers(client):
    token = client.post(
        "/auth/login", json={"username": "admin", "password": "admin"}
    ).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- authentication ----------

def test_login_with_default_admin(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["role"] == "Admin" and body["token"]


def test_login_rejects_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_admin_password_comes_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret-pass")
    app = create_app(database=str(tmp_path / "env.db"))
    c = app.test_client()
    assert c.post("/auth/login", json={"username": "admin", "password": "admin"}).status_code == 401
    assert c.post("/auth/login",
                  json={"username": "admin", "password": "s3cret-pass"}).status_code == 200


def test_passwords_are_hashed_at_rest(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    stored = conn.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()[0]
    conn.close()
    assert stored != "admin"


def test_me_requires_token(client, admin_headers):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert client.get("/auth/me", headers=admin_headers).get_json()["role"] == "Admin"


def test_admin_creates_trainer_who_cannot_create_users(client, admin_headers):
    resp = client.post("/auth/users", headers=admin_headers,
                       json={"username": "coach", "password": "coach123", "role": "Trainer"})
    assert resp.status_code == 201
    assert client.post("/auth/users", headers=admin_headers,
                       json={"username": "coach", "password": "coach123"}).status_code == 409

    token = client.post("/auth/login", json={"username": "coach", "password": "coach123"}
                        ).get_json()["token"]
    trainer = {"Authorization": f"Bearer {token}"}
    resp = client.post("/auth/users", headers=trainer,
                       json={"username": "x", "password": "xxxxxx"})
    assert resp.status_code == 403


def test_create_user_validation(client, admin_headers):
    assert client.post("/auth/users", headers=admin_headers,
                       json={"username": "a", "password": "123"}).status_code == 400
    assert client.post("/auth/users", headers=admin_headers,
                       json={"username": "a", "password": "123456", "role": "God"}
                       ).status_code == 400


# ---------- client deletion (Admin only) ----------

def test_delete_client_requires_admin(client, make_client, admin_headers):
    make_client()
    client.post("/clients/Asha/workouts", json={"workout_type": "Cardio"})
    assert client.delete("/clients/Asha").status_code == 401
    assert client.delete("/clients/Asha", headers=admin_headers).status_code == 204
    assert client.get("/clients/Asha").status_code == 404
    assert client.delete("/clients/Asha", headers=admin_headers).status_code == 404


# ---------- membership: pure rules ----------

def test_membership_state_active_and_expired():
    active = membership_state("Active", (TODAY + timedelta(days=10)).isoformat(), TODAY)
    assert active["active"] and active["days_remaining"] == 10
    expired = membership_state("Active", (TODAY - timedelta(days=1)).isoformat(), TODAY)
    assert expired["status"] == "Expired" and not expired["active"]
    assert membership_state(None, None, TODAY)["status"] == "None"


def test_renewal_extends_from_later_of_today_or_end():
    assert renewed_end(None, 1, TODAY) == TODAY + timedelta(days=30)
    future = (TODAY + timedelta(days=5)).isoformat()
    assert renewed_end(future, 2, TODAY) == TODAY + timedelta(days=65)
    past = (TODAY - timedelta(days=100)).isoformat()
    assert renewed_end(past, 1, TODAY) == TODAY + timedelta(days=30)


# ---------- membership: API ----------

def test_new_client_gets_trial_membership(client, make_client):
    make_client()
    body = client.get("/clients/Asha/membership").get_json()
    assert body["status"] == "Active"
    assert body["days_remaining"] == 30


def test_updating_client_keeps_membership(client, make_client, admin_headers):
    make_client()
    client.post("/clients/Asha/membership/renew", headers=admin_headers, json={"months": 3})
    make_client(weight=72)  # update profile
    body = client.get("/clients/Asha/membership").get_json()
    assert body["days_remaining"] == 30 + 90
    assert client.get("/clients/Asha").get_json()["weight"] == 72


def test_renew_requires_token_and_valid_months(client, make_client, admin_headers):
    make_client()
    assert client.post("/clients/Asha/membership/renew", json={"months": 1}).status_code == 401
    assert client.post("/clients/Asha/membership/renew", headers=admin_headers,
                       json={"months": 0}).status_code == 400
    assert client.post("/clients/Ghost/membership/renew", headers=admin_headers,
                       json={"months": 1}).status_code == 404
    assert client.get("/clients/Ghost/membership").status_code == 404


def test_migration_upgrades_v1_database(tmp_path):
    """A database created by v1.x (no membership columns) is upgraded in place."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "name TEXT UNIQUE NOT NULL, age INTEGER, height REAL, weight REAL, "
                 "program TEXT, calories INTEGER, target_weight REAL, target_adherence INTEGER)")
    conn.execute("INSERT INTO clients (name, program) VALUES ('Old', 'Beginner (BG)')")
    conn.commit()
    conn.close()

    c = create_app(database=str(path)).test_client()
    assert c.get("/clients/Old/membership").get_json()["status"] == "None"
