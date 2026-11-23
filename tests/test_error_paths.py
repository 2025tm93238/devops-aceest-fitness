"""Error-path tests: every endpoint rejects bad input and unknown clients cleanly."""

import pytest

import auth
from fitness import calculate_bmi


@pytest.mark.parametrize("method, path", [
    ("get", "/clients/Ghost/bmi"),
    ("post", "/clients/Ghost/workouts"),
    ("get", "/clients/Ghost/workouts"),
    ("post", "/clients/Ghost/metrics"),
    ("get", "/clients/Ghost/metrics"),
    ("post", "/clients/Ghost/progress"),
    ("get", "/clients/Ghost/summary"),
    ("get", "/clients/Ghost/report.pdf"),
])
def test_unknown_client_returns_404(client, method, path):
    resp = getattr(client, method)(path, json={})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "client not found"


def test_create_client_rejects_negative_weight(client):
    resp = client.post("/clients", json={"name": "Neg", "weight": -5, "program": "Beginner (BG)"})
    assert resp.status_code == 400


def test_bmi_needs_height_and_weight(client, make_client):
    make_client(height=None)
    assert client.get("/clients/Asha/bmi").status_code == 400


def test_progress_requires_adherence_and_defaults_week(client, make_client):
    make_client()
    assert client.post("/clients/Asha/progress", json={}).status_code == 400
    body = client.post("/clients/Asha/progress", json={"adherence": 70}).get_json()
    assert body["week"].startswith("Week ")


@pytest.mark.parametrize("weight, height", [(0, 170), (70, 0), (None, 170)])
def test_calculate_bmi_rejects_bad_input(weight, height):
    with pytest.raises(ValueError):
        calculate_bmi(weight, height)


def test_expired_token_is_rejected(client, monkeypatch):
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}
                        ).get_json()["token"]
    monkeypatch.setattr(auth, "TOKEN_MAX_AGE_SECONDS", -1)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "token expired"


def test_list_metrics_newest_first(client, make_client):
    make_client()
    client.post("/clients/Asha/metrics", json={"date": "2026-01-01", "weight": 71})
    client.post("/clients/Asha/metrics", json={"date": "2026-02-01", "weight": 69})
    rows = client.get("/clients/Asha/metrics").get_json()
    assert [r["weight"] for r in rows] == [69, 71]
