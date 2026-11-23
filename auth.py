"""Role-based authentication (ported from the login screen in Aceestver-3.2.4).

Improvements over the desktop version:
- passwords are stored as salted hashes (werkzeug), never in plain text;
- login returns a signed, time-limited bearer token instead of holding state
  in a GUI session, so the API stays stateless and horizontally scalable.
"""

import os
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

ROLES = ("Admin", "Trainer")
TOKEN_MAX_AGE_SECONDS = 8 * 60 * 60  # one working shift

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="aceest-auth")


def create_user(username, password, role):
    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role),
    )
    db.commit()


def seed_admin(app):
    """Create the default admin account on first start (as the desktop app did).

    The password comes from the ADMIN_PASSWORD environment variable, which the
    Kubernetes manifests populate from a Secret.

    Several gunicorn workers start at the same moment against the same database,
    so the insert must be idempotent: INSERT OR IGNORE lets exactly one worker win
    instead of the others crashing on the primary-key constraint.
    """
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin")), "Admin"),
        )
        db.commit()


def require_role(*roles):
    """Decorator: reject the request unless it carries a valid token for one of ``roles``."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify(error="authentication required"), 401
            try:
                claims = _serializer().loads(header[7:], max_age=TOKEN_MAX_AGE_SECONDS)
            except SignatureExpired:
                return jsonify(error="token expired"), 401
            except BadSignature:
                return jsonify(error="invalid token"), 401
            if claims.get("role") not in roles:
                return jsonify(error="insufficient role"), 403
            g.user = claims
            return view(*args, **kwargs)

        return wrapped

    return decorator


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    row = get_db().execute(
        "SELECT username, password_hash, role FROM users WHERE username=?", (username,)
    ).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return jsonify(error="invalid credentials"), 401
    token = _serializer().dumps({"sub": row["username"], "role": row["role"]})
    return jsonify(token=token, username=row["username"], role=row["role"])


@bp.post("/users")
@require_role("Admin")
def add_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "Trainer")
    if not username or len(password) < 6:
        return jsonify(error="username and a password of at least 6 characters required"), 400
    if role not in ROLES:
        return jsonify(error=f"role must be one of {list(ROLES)}"), 400
    if get_db().execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        return jsonify(error="user already exists"), 409
    create_user(username, password, role)
    return jsonify(username=username, role=role), 201


@bp.get("/me")
@require_role(*ROLES)
def me():
    return jsonify(username=g.user["sub"], role=g.user["role"])
