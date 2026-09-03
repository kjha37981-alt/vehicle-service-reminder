"""
app.py
------
Flask routes for the Vehicle Service Reminder app.
Same pattern as before: GET shows the form, POST processes it and
hands off to analyzer.py to do the real work.
"""

from flask import Flask, render_template, request, flash
from datetime import date, datetime
from analyzer import VehicleServiceAnalyzer, SERVICE_INTERVALS

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-if-needed"

SERVICE_TYPES = list(SERVICE_INTERVALS.keys())


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        today=date.today().isoformat(),
        service_types=SERVICE_TYPES,
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    raw_text = request.form.get("service_log", "").strip()
    mileage_str = request.form.get("current_mileage", "").strip()
    date_str = request.form.get("current_date", "").strip()

    if not raw_text:
        flash("Please paste a service log before analyzing.")
        return render_template("index.html", today=date.today().isoformat(), service_types=SERVICE_TYPES)

    try:
        current_mileage = int(mileage_str)
    except ValueError:
        flash("Current mileage must be a number.")
        return render_template("index.html", today=date.today().isoformat(), service_types=SERVICE_TYPES)

    try:
        current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        current_date = date.today()

    analyzer = VehicleServiceAnalyzer(raw_text, current_mileage, current_date)

    if not analyzer.records:
        flash(
            "No valid service records detected. Make sure each line follows: "
            "'Service Type, YYYY-MM-DD, mileage, cost' — e.g. 'Oil Change, 2026-01-15, 12000, 1500'."
        )
        return render_template(
            "index.html", today=date.today().isoformat(),
            service_types=SERVICE_TYPES, previous_text=raw_text,
        )

    report = analyzer.full_report()
    return render_template("results.html", report=report, current_mileage=current_mileage,
                            current_date=current_date.isoformat())


if __name__ == "__main__":
    app.run(debug=True)
