"""Tests for v1.1.0: version metadata and CSV export."""

import csv
import io

from version import __version__


def test_version_is_semver():
    parts = __version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_health_reports_version(client):
    body = client.get("/health").get_json()
    assert body == {"status": "ok", "version": __version__}


def test_version_endpoint_defaults_to_local_track(client, monkeypatch):
    monkeypatch.delenv("DEPLOYMENT_TRACK", raising=False)
    body = client.get("/version").get_json()
    assert body["version"] == __version__
    assert body["track"] == "local"
    assert body["pod"]


def test_version_endpoint_reports_deployment_track(client, monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_TRACK", "canary")
    assert client.get("/version").get_json()["track"] == "canary"


def test_index_lists_endpoints_and_version(client):
    body = client.get("/").get_json()
    assert body["version"] == __version__
    assert "GET  /export/clients.csv" in body["endpoints"]


def test_csv_export_empty_has_header_only(client):
    resp = client.get("/export/clients.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert rows == [["name", "age", "height", "weight", "program", "calories",
                     "target_weight", "target_adherence"]]


def test_csv_export_contains_clients_sorted(client, make_client):
    make_client(name="Ravi", weight=80, program="Beginner (BG)")
    make_client(name="Asha")
    resp = client.get("/export/clients.csv")
    assert "attachment" in resp.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert [r["name"] for r in rows] == ["Asha", "Ravi"]
    assert rows[1]["calories"] == "2080"  # 80 kg * 26 (Beginner)
