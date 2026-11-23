"""Membership status and renewal (ported from check_membership in Aceestver-3.2.4)."""

from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from auth import ROLES, require_role
from db import CLIENT_NOT_FOUND, client_row, get_db

TRIAL_DAYS = 30
MAX_RENEWAL_MONTHS = 24
DAYS_PER_MONTH = 30

bp = Blueprint("membership", __name__)


def membership_state(status, end, today=None):
    """Derive the effective membership state from stored status and end date.

    Pure function (no I/O) so the business rule is easy to unit test.
    """
    today = today or date.today()
    if not status:
        return {"status": "None", "membership_end": None, "active": False, "days_remaining": 0}
    end_date = date.fromisoformat(end) if end else None
    if end_date is not None and end_date < today:
        status = "Expired"
    days = (end_date - today).days if end_date and end_date >= today else 0
    return {
        "status": status,
        "membership_end": end,
        "active": status == "Active",
        "days_remaining": days,
    }


def renewed_end(current_end, months, today=None):
    """New end date: extend from the later of today or the current end date."""
    today = today or date.today()
    start = today
    if current_end:
        start = max(today, date.fromisoformat(current_end))
    return start + timedelta(days=months * DAYS_PER_MONTH)


def start_trial(name):
    """Give a newly created client an Active trial membership (if none set yet)."""
    db = get_db()
    db.execute(
        "UPDATE clients SET membership_status='Active', membership_end=? "
        "WHERE name=? AND membership_status IS NULL",
        ((date.today() + timedelta(days=TRIAL_DAYS)).isoformat(), name),
    )
    db.commit()


@bp.get("/clients/<name>/membership")
def get_membership(name):
    row = client_row(name)
    if row is None:
        return jsonify(error=CLIENT_NOT_FOUND), 404
    state = membership_state(row["membership_status"], row["membership_end"])
    return jsonify(name=name, **state)


@bp.post("/clients/<name>/membership/renew")
@require_role(*ROLES)
def renew_membership(name):
    row = client_row(name)
    if row is None:
        return jsonify(error=CLIENT_NOT_FOUND), 404
    data = request.get_json(silent=True) or {}
    months = data.get("months", 1)
    if not isinstance(months, int) or not 1 <= months <= MAX_RENEWAL_MONTHS:
        return jsonify(error=f"months must be an integer 1-{MAX_RENEWAL_MONTHS}"), 400
    new_end = renewed_end(row["membership_end"], months).isoformat()
    db = get_db()
    db.execute(
        "UPDATE clients SET membership_status='Active', membership_end=? WHERE name=?",
        (new_end, name),
    )
    db.commit()
    return jsonify(name=name, **membership_state("Active", new_end))
