"""PDF client report (ported from export_pdf_report in Aceestver-3.1.2 / 3.2.4).

The desktop app wrote the PDF to the local disk; the API renders it in memory
and streams it to the caller, so containers stay stateless.
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from version import __version__

BRAND = (212, 175, 55)  # ACEest gold, as in the desktop UI
NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _latin1(value):
    """Core PDF fonts are Latin-1 only; replace anything else instead of failing."""
    return str(value).encode("latin-1", "replace").decode("latin-1")


def _row(pdf, label, value):
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(55, 8, _latin1(label))
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, _latin1("-" if value is None else value), **NEXT_LINE)


def _heading(pdf, text):
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 9, _latin1(text), **NEXT_LINE)
    pdf.set_text_color(0, 0, 0)


def build_client_report(client, bmi, membership, summary, workouts, generated_on):
    """Render a client report and return the PDF as bytes.

    All inputs are plain dicts/lists so the function has no database dependency.
    """
    pdf = FPDF()
    pdf.set_title(_latin1(f"ACEest Client Report - {client['name']}"))
    pdf.set_creator(f"ACEest Fitness API v{__version__}")
    pdf.add_page()

    pdf.set_fill_color(*BRAND)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, _latin1(f"ACEest Client Report - {client['name']}"),
             align="C", fill=True, **NEXT_LINE)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, f"Generated {generated_on} by ACEest Fitness API v{__version__}",
             align="C", **NEXT_LINE)

    _heading(pdf, "Profile")
    _row(pdf, "Age", client.get("age"))
    _row(pdf, "Height", f"{client['height']} cm" if client.get("height") else None)
    _row(pdf, "Weight", f"{client['weight']} kg" if client.get("weight") else None)
    _row(pdf, "Program", client.get("program"))
    _row(pdf, "Daily calories", f"{client['calories']} kcal" if client.get("calories") else None)
    if bmi:
        _row(pdf, "BMI", f"{bmi['bmi']} ({bmi['category']})")

    _heading(pdf, "Membership")
    _row(pdf, "Status", membership["status"])
    _row(pdf, "Renewal date", membership["membership_end"])
    _row(pdf, "Days remaining", membership["days_remaining"])

    _heading(pdf, "Progress")
    _row(pdf, "Weeks logged", summary["weeks_logged"])
    _row(pdf, "Average adherence", f"{summary['average_adherence']} %")
    _row(pdf, "Workouts logged", summary["workouts_logged"])

    _heading(pdf, "Recent workouts")
    if not workouts:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "No workouts logged yet.", **NEXT_LINE)
    else:
        pdf.set_font("Helvetica", "B", 10)
        for title, width in (("Date", 35), ("Type", 45), ("Minutes", 25), ("Notes", 0)):
            pdf.cell(width, 8, title, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 10)
        for w in workouts:
            pdf.cell(35, 8, _latin1(w.get("date") or ""), border=1)
            pdf.cell(45, 8, _latin1(w.get("workout_type") or ""), border=1)
            pdf.cell(25, 8, _latin1(w.get("duration_min") or ""), border=1)
            pdf.cell(0, 8, _latin1((w.get("notes") or "")[:60]), border=1, **NEXT_LINE)

    return bytes(pdf.output())
