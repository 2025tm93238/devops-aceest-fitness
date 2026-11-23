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

import auth
import membership
from auth import require_role
from db import CLIENT_NOT_FOUND, client_row, close_db, get_db, init_db
from fitness import PROGRAMS, bmi_category, calculate_bmi, calculate_calories
from membership import membership_state, start_trial
from planner import generate_plan
from reports import build_client_report
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
    "POST /clients/<name>/program/generate",
    "GET  /clients/<name>/report.pdf",
    "DELETE /clients/<name>            (Admin)",
    "GET  /export/clients.csv",
    "POST /auth/login",
    "GET  /auth/me                     (token)",
    "POST /auth/users                  (Admin)",
    "GET  /clients/<name>/membership",
    "POST /clients/<name>/membership/renew (token)",
]

CSV_COLUMNS = ["name", "age", "height", "weight", "program", "calories",
               "target_weight", "target_adherence"]
CSV_QUERY = (
    "SELECT name, age, height, weight, program, calories, target_weight, "
    "target_adherence FROM clients ORDER BY name"
)

# Child rows first, then the client itself.
DELETE_CLIENT_QUERIES = (
    "DELETE FROM workouts WHERE client_name=?",
    "DELETE FROM metrics WHERE client_name=?",
    "DELETE FROM progress WHERE client_name=?",
    "DELETE FROM clients WHERE name=?",
)


def summary_data(name):
    """Aggregate progress, workout and metric figures for one client."""
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
    return {
        "weeks_logged": weeks,
        "average_adherence": round(avg, 1) if avg is not None else 0,
        "workouts_logged": workouts,
        "last_metric": dict(last_metric) if last_metric else None,
    }


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
    # CSRF protection (S4502) does not apply: this is a stateless JSON API that
    # authenticates with bearer tokens in a header, never with cookies.
    app = Flask(__name__)  # NOSONAR
    app.config["DATABASE"] = database or os.environ.get("DATABASE", "aceest_fitness.db")
    # Signs auth tokens. Must be identical across replicas, so in Kubernetes it
    # is injected from a Secret; the fallback is for local development only.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    app.teardown_appcontext(close_db)
    init_db(app)
    auth.seed_admin(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(membership.bp)

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
            """INSERT INTO clients
               (name, age, height, weight, program, calories, target_weight, target_adherence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 age=excluded.age, height=excluded.height, weight=excluded.weight,
                 program=excluded.program, calories=excluded.calories,
                 target_weight=excluded.target_weight,
                 target_adherence=excluded.target_adherence""",
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
        start_trial(name)
        return jsonify(dict(client_row(name))), 201

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        row = client_row(name)
        if row is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
        return jsonify(dict(row))

    @app.delete("/clients/<name>")
    @require_role("Admin")
    def delete_client(name):
        if client_row(name) is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
        db = get_db()
        for query in DELETE_CLIENT_QUERIES:
            db.execute(query, (name,))
        db.commit()
        return "", 204

    @app.get("/clients/<name>/bmi")
    def client_bmi(name):
        row = client_row(name)
        if row is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
        if not row["height"] or not row["weight"]:
            return jsonify(error="client has no height/weight recorded"), 400
        bmi = calculate_bmi(row["weight"], row["height"])
        category, risk = bmi_category(bmi)
        return jsonify(name=name, bmi=bmi, category=category, risk=risk)

    @app.post("/clients/<name>/workouts")
    def log_workout(name):
        if client_row(name) is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
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
            return jsonify(error=CLIENT_NOT_FOUND), 404
        rows = get_db().execute(
            "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/metrics")
    def log_metrics(name):
        if client_row(name) is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
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
            return jsonify(error=CLIENT_NOT_FOUND), 404
        rows = get_db().execute(
            "SELECT * FROM metrics WHERE client_name=? ORDER BY date DESC, id DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/progress")
    def log_progress(name):
        if client_row(name) is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
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
            return jsonify(error=CLIENT_NOT_FOUND), 404
        return jsonify(client=dict(row), **summary_data(name))

    @app.get("/clients/<name>/report.pdf")
    def client_report(name):
        """Downloadable PDF report (ported from Aceestver-3.1.2 / 3.2.4)."""
        row = client_row(name)
        if row is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
        client = dict(row)
        bmi = None
        if client["height"] and client["weight"]:
            value = calculate_bmi(client["weight"], client["height"])
            bmi = {"bmi": value, "category": bmi_category(value)[0]}
        recent = get_db().execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts "
            "WHERE client_name=? ORDER BY date DESC, id DESC LIMIT 10",
            (name,),
        ).fetchall()
        pdf = build_client_report(
            client=client,
            bmi=bmi,
            membership=membership_state(client["membership_status"], client["membership_end"]),
            summary=summary_data(name),
            workouts=[dict(r) for r in recent],
            generated_on=date.today().isoformat(),
        )
        filename = f"{name.replace(' ', '_')}_report.pdf"
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.post("/clients/<name>/program/generate")
    def generate_program(name):
        """AI-style weekly plan based on the client's program and experience."""
        row = client_row(name)
        if row is None:
            return jsonify(error=CLIENT_NOT_FOUND), 404
        data = request.get_json(silent=True) or {}
        try:
            plan = generate_plan(row["program"], data.get("experience"), data.get("seed"))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(name=name, program=row["program"], **plan)

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
