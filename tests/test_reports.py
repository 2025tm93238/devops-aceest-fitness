"""Tests for v3.0.0: PDF client report."""

from reports import build_client_report


def _report(**overrides):
    args = {
        "client": {"name": "Asha", "age": 30, "height": 170, "weight": 70,
                   "program": "Beginner (BG)", "calories": 1820},
        "bmi": {"bmi": 24.2, "category": "Normal"},
        "membership": {"status": "Active", "membership_end": "2026-12-23",
                       "days_remaining": 30, "active": True},
        "summary": {"weeks_logged": 0, "average_adherence": 0, "workouts_logged": 0},
        "workouts": [],
        "generated_on": "2026-11-23",
    }
    args.update(overrides)
    return build_client_report(**args)


def test_report_is_a_pdf():
    pdf = _report()
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_report_handles_non_latin_names_and_missing_values():
    pdf = _report(client={"name": "Anaïs नमस्ते"}, bmi=None,
                  workouts=[{"date": None, "workout_type": "Cardio", "duration_min": None,
                             "notes": None}])
    assert pdf.startswith(b"%PDF-")


def test_report_endpoint_streams_pdf(client, make_client):
    make_client(name="Asha Rao")
    client.post("/clients/Asha Rao/workouts",
                json={"workout_type": "Strength", "duration_min": 45, "notes": "PR day"})
    client.post("/clients/Asha Rao/progress", json={"adherence": 90})
    resp = client.get("/clients/Asha Rao/report.pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert "Asha_Rao_report.pdf" in resp.headers["Content-Disposition"]
    assert resp.data.startswith(b"%PDF-")


def test_report_endpoint_missing_client(client):
    assert client.get("/clients/Ghost/report.pdf").status_code == 404


def test_report_without_height_or_weight(client, make_client):
    make_client(height=None, weight=None)
    assert client.get("/clients/Asha/report.pdf").status_code == 200
