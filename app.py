"""ACEest Fitness & Gym - Flask REST API.

This re-implements the core logic of the original Tkinter desktop prototypes
(see ``versions/``) as a web service so it can be tested, containerized and
deployed through a CI/CD pipeline. Data is persisted in SQLite.
"""

import csv
import io
import os
import socket
from datetime import date, datetime

from flask import Flask, Response, jsonify, request

from db import client_row, close_db, get_db, init_db
from fitness import PROGRAMS, bmi_category, calculate_bmi, calculate_calories
from version import __version__

ENDPOINTS = [
    "GET  /health",
    "GET  /version",
    "GET  /programs",
    "POST /clients",
    "GET  /clients",
    "GET  /clients/<name>",
    "GET  /clients/<name>/bmi",
    "POST /clients/<name>/workouts",
    "GET  /clients/<name>/workouts",
    "POST /clients/<name>/metrics",
    "GET  /clients/<name>/metrics",
    "POST /clients/<name>/progress",
    "GET  /clients/<name>/summary",
    "GET  /export/clients.csv",
]

CSV_COLUMNS = ["name", "age", "height", "weight", "program", "calories",
               "target_weight", "target_adherence"]
CSV_QUERY = (
    "SELECT name, age, height, weight, program, calories, target_weight, "
    "target_adherence FROM clients ORDER BY name"
)


def version_info():
    """Build metadata identifying exactly which build and deployment answered.

    ``DEPLOYMENT_TRACK`` (e.g. blue / green / stable / canary) is injected by the
    Kubernetes manifests so deployment strategies can be observed from outside.
    """
    return {
        "app": "ACEest Fitness & Gym API",
        "version": __version__,
        "track": os.environ.get("DEPLOYMENT_TRACK", "local"),
        "pod": socket.gethostname(),
    }


# ---------- application factory ----------

def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("DATABASE", "aceest_fitness.db")
    app.teardown_appcontext(close_db)
    init_db(app)

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=__version__), 200

    @app.get("/version")
    def version():
        return jsonify(version_info())

    @app.get("/")
    def index():
        return jsonify(**version_info(), endpoints=ENDPOINTS)

    @app.get("/programs")
    def list_programs():
        return jsonify(PROGRAMS)

    @app.post("/clients")
    def create_client():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        program = data.get("program")
        if not name:
            return jsonify(error="name is required"), 400
        if program not in PROGRAMS:
            return jsonify(error="a valid program is required"), 400

        weight = data.get("weight")
        calories = None
        if weight:
            try:
                calories = calculate_calories(weight, program)
            except ValueError as exc:
                return jsonify(error=str(exc)), 400

        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO clients
               (name, age, height, weight, program, calories, target_weight, target_adherence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                data.get("age"),
                data.get("height"),
                weight,
                program,
                calories,
                data.get("target_weight"),
                data.get("target_adherence"),
            ),
        )
        db.commit()
        return jsonify(dict(client_row(name))), 201

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        row = client_row(name)
        if row is None:
            return jsonify(error="client not found"), 404
        return jsonify(dict(row))

    @app.get("/clients/<name>/bmi")
    def client_bmi(name):
        row = client_row(name)
        if row is None:
            return jsonify(error="client not found"), 404
        if not row["height"] or not row["weight"]:
            return jsonify(error="client has no height/weight recorded"), 400
        bmi = calculate_bmi(row["weight"], row["height"])
        category, risk = bmi_category(bmi)
        return jsonify(name=name, bmi=bmi, category=category, risk=risk)

    @app.post("/clients/<name>/workouts")
    def log_workout(name):
        if client_row(name) is None:
            return jsonify(error="client not found"), 404
        data = request.get_json(silent=True) or {}
        workout_type = (data.get("workout_type") or "").strip()
        if not workout_type:
            return jsonify(error="workout_type is required"), 400
        db = get_db()
        cur = db.execute(
            """INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                name,
                data.get("date") or date.today().isoformat(),
                workout_type,
                data.get("duration_min"),
                data.get("notes"),
            ),
        )
        db.commit()
        return jsonify(id=cur.lastrowid, client_name=name, workout_type=workout_type), 201

    @app.get("/clients/<name>/workouts")
    def list_workouts(name):
        if client_row(name) is None:
            return jsonify(error="client not found"), 404
        rows = get_db().execute(
            "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/metrics")
    def log_metrics(name):
        if client_row(name) is None:
            return jsonify(error="client not found"), 404
        data = request.get_json(silent=True) or {}
        db = get_db()
        cur = db.execute(
            """INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
               VALUES (?, ?, ?, ?, ?)""",
            (
                name,
                data.get("date") or date.today().isoformat(),
                data.get("weight"),
                data.get("waist"),
                data.get("bodyfat"),
            ),
        )
        db.commit()
        return jsonify(id=cur.lastrowid, client_name=name), 201

    @app.get("/clients/<name>/metrics")
    def list_metrics(name):
        if client_row(name) is None:
            return jsonify(error="client not found"), 404
        rows = get_db().execute(
            "SELECT * FROM metrics WHERE client_name=? ORDER BY date DESC, id DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/progress")
    def log_progress(name):
        if client_row(name) is None:
            return jsonify(error="client not found"), 404
        data = request.get_json(silent=True) or {}
        adherence = data.get("adherence")
        if adherence is None:
            return jsonify(error="adherence is required"), 400
        week = data.get("week") or datetime.now().strftime("Week %U - %Y")
        db = get_db()
        cur = db.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            (name, week, int(adherence)),
        )
        db.commit()
        return jsonify(id=cur.lastrowid, client_name=name, week=week, adherence=int(adherence)), 201

    @app.get("/clients/<name>/summary")
    def client_summary(name):
        row = client_row(name)
        if row is None:
            return jsonify(error="client not found"), 404
        db = get_db()
        weeks, avg = db.execute(
            "SELECT COUNT(*), AVG(adherence) FROM progress WHERE client_name=?", (name,)
        ).fetchone()
        workouts = db.execute(
            "SELECT COUNT(*) FROM workouts WHERE client_name=?", (name,)
        ).fetchone()[0]
        last_metric = db.execute(
            "SELECT date, weight, waist, bodyfat FROM metrics "
            "WHERE client_name=? ORDER BY date DESC LIMIT 1",
            (name,),
        ).fetchone()
        return jsonify(
            client=dict(row),
            weeks_logged=weeks,
            average_adherence=round(avg, 1) if avg is not None else 0,
            workouts_logged=workouts,
            last_metric=dict(last_metric) if last_metric else None,
        )

    @app.get("/export/clients.csv")
    def export_clients_csv():
        """Export all clients as CSV (ported from Aceestver1.1.2 export_csv)."""
        rows = get_db().execute(CSV_QUERY).fetchall()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(tuple(r) for r in rows)
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=clients.csv"},
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
