"""Pytest suite for the ACEest Fitness & Gym API.

Covers the pure domain logic (BMI, calories) and the Flask endpoints end to end
against a throwaway SQLite database.
"""

import pytest

from fitness import bmi_category, calculate_bmi, calculate_calories


# ---------- pure domain logic ----------

def test_calculate_bmi_normal():
    # 70 kg at 170 cm -> 24.2
    assert calculate_bmi(70, 170) == 24.2


def test_bmi_category_boundaries():
    assert bmi_category(17)[0] == "Underweight"
    assert bmi_category(22)[0] == "Normal"
    assert bmi_category(27)[0] == "Overweight"
    assert bmi_category(32)[0] == "Obese"


def test_calculate_calories_uses_program_factor():
    # 70 kg * factor 35 for the PPL program
    assert calculate_calories(70, "Muscle Gain (MG) - PPL") == 2450


def test_calculate_calories_rejects_bad_input():
    with pytest.raises(ValueError):
        calculate_calories(0, "Beginner (BG)")
    with pytest.raises(ValueError):
        calculate_calories(70, "Nonexistent Program")


# ---------- health & metadata ----------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_programs_listing(client):
    resp = client.get("/programs")
    assert resp.status_code == 200
    assert "Beginner (BG)" in resp.get_json()


# ---------- client CRUD ----------

def test_create_client_computes_calories(client, make_client):
    resp = make_client()
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Asha"
    assert body["calories"] == 2450  # 70 * 35


def test_create_client_requires_name(client):
    resp = client.post("/clients", json={"program": "Beginner (BG)"})
    assert resp.status_code == 400


def test_create_client_requires_valid_program(client):
    resp = client.post("/clients", json={"name": "Bob", "program": "Bad"})
    assert resp.status_code == 400


def test_get_missing_client_returns_404(client):
    assert client.get("/clients/Ghost").status_code == 404


def test_create_then_fetch_and_list(client, make_client):
    make_client(name="Asha")
    make_client(name="Ravi")
    assert client.get("/clients/Asha").status_code == 200
    names = [c["name"] for c in client.get("/clients").get_json()]
    assert names == ["Asha", "Ravi"]  # ordered by name


# ---------- BMI endpoint ----------

def test_client_bmi_endpoint(client, make_client):
    make_client()
    body = client.get("/clients/Asha/bmi").get_json()
    assert body["bmi"] == 24.2
    assert body["category"] == "Normal"


# ---------- workouts, metrics, progress, summary ----------

def test_workout_logging_and_history(client, make_client):
    make_client()
    resp = client.post(
        "/clients/Asha/workouts",
        json={"workout_type": "Strength", "duration_min": 60, "notes": "heavy day"},
    )
    assert resp.status_code == 201
    history = client.get("/clients/Asha/workouts").get_json()
    assert len(history) == 1
    assert history[0]["workout_type"] == "Strength"


def test_workout_requires_type(client, make_client):
    make_client()
    resp = client.post("/clients/Asha/workouts", json={"duration_min": 30})
    assert resp.status_code == 400


def test_metrics_and_progress_feed_summary(client, make_client):
    make_client()
    client.post("/clients/Asha/metrics", json={"weight": 69, "waist": 80, "bodyfat": 18})
    client.post("/clients/Asha/progress", json={"adherence": 80, "week": "Week 01 - 2026"})
    client.post("/clients/Asha/progress", json={"adherence": 100, "week": "Week 02 - 2026"})

    summary = client.get("/clients/Asha/summary").get_json()
    assert summary["weeks_logged"] == 2
    assert summary["average_adherence"] == 90.0
    assert summary["last_metric"]["weight"] == 69
