"""
analyzer.py
-----------
Core logic for the Vehicle Service Reminder app. No Flask code here —
pure Python, so it's easy to read, test, and reuse on its own.

Python concepts used in this file:
  - datetime          -> comparing dates, calculating "days since"
  - dataclasses        -> clean data model for a ServiceRecord
  - dictionaries        -> service interval rulebook (km + month limits)
  - collections.Counter -> cost totals grouped by service type
  - sorting with a key function -> ranking reminders by urgency
  - list/dict comprehensions
"""

from dataclasses import dataclass
from datetime import date, datetime
from collections import Counter


# ---------------------------------------------------------------------------
# 1. THE SERVICE RULEBOOK
# ---------------------------------------------------------------------------
# For each service type: how many KM or MONTHS can pass before it's due.
# Whichever limit is hit FIRST triggers the reminder (that's how real
# service manuals define intervals too).
SERVICE_INTERVALS = {
    "Oil Change":     {"km": 5000,  "months": 6},
    "Air Filter":     {"km": 10000, "months": 12},
    "Brake Pads":     {"km": 20000, "months": 24},
    "Tyre Rotation":  {"km": 10000, "months": 6},
    "Battery Check":  {"km": 15000, "months": 12},
    "Coolant Flush":  {"km": 40000, "months": 24},
    "Timing Belt":    {"km": 60000, "months": 60},
}


# ---------------------------------------------------------------------------
# 2. DATA MODEL
# ---------------------------------------------------------------------------
@dataclass
class ServiceRecord:
    service_type: str
    service_date: date
    mileage: int
    cost: float

    def to_dict(self):
        return {
            "service_type": self.service_type,
            "date": self.service_date.isoformat(),
            "mileage": self.mileage,
            "cost": self.cost,
        }


# ---------------------------------------------------------------------------
# 3. THE MAIN ANALYZER CLASS
# ---------------------------------------------------------------------------
class VehicleServiceAnalyzer:
    """
    Takes a raw pasted service log + the vehicle's current mileage/date,
    and produces:
      - service interval tracking (last done, km/time since)
      - due reminders (ranked by urgency)
      - cost history (totals, per-type, averages)
      - mileage log summary (usage rate)
      - maintenance forecast (predicted due dates + upcoming cost estimate)
    """

    def __init__(self, raw_text: str, current_mileage: int, current_date: date):
        self.current_mileage = current_mileage
        self.current_date = current_date
        self.records = self._parse(raw_text)

    # ---- PARSING -----------------------------------------------------
    def _parse(self, raw_text: str):
        """
        Expected line format (comma separated):
            Service Type, YYYY-MM-DD, mileage, cost
        e.g.
            Oil Change, 2026-01-15, 12000, 1500
        """
        records = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 4:
                continue  # skip malformed lines
            service_type, date_str, mileage_str, cost_str = parts
            try:
                service_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                mileage = int(mileage_str)
                cost = float(cost_str)
            except ValueError:
                continue  # skip lines with bad numbers/dates
            records.append(ServiceRecord(service_type, service_date, mileage, cost))
        # Oldest first makes "last service" lookups simple (just take the last match)
        records.sort(key=lambda r: r.service_date)
        return records

    # ---- HELPER: most recent record for a service type -----------------
    def _last_service(self, service_type: str):
        matches = [r for r in self.records if r.service_type == service_type]
        return matches[-1] if matches else None

    # ---- FEATURE 1: SERVICE INTERVAL TRACKING ---------------------------
    def interval_tracking(self):
        """
        For every known service type, work out how far the vehicle has
        gone (km and days) since it was last done, and how that compares
        to the allowed interval.
        """
        results = []
        for service_type, limits in SERVICE_INTERVALS.items():
            last = self._last_service(service_type)

            if last is None:
                results.append({
                    "service_type": service_type,
                    "last_done": None,
                    "km_since": None,
                    "days_since": None,
                    "km_limit": limits["km"],
                    "month_limit": limits["months"],
                    "status": "NEVER DONE",
                })
                continue

            km_since = self.current_mileage - last.mileage
            days_since = (self.current_date - last.service_date).days

            km_pct = km_since / limits["km"]
            time_pct = days_since / (limits["months"] * 30)  # approx days/month
            worst_pct = max(km_pct, time_pct)

            if worst_pct >= 1.0:
                status = "OVERDUE"
            elif worst_pct >= 0.85:
                status = "DUE SOON"
            else:
                status = "OK"

            results.append({
                "service_type": service_type,
                "last_done": last.service_date.isoformat(),
                "km_since": km_since,
                "days_since": days_since,
                "km_limit": limits["km"],
                "month_limit": limits["months"],
                "status": status,
                "urgency_pct": round(worst_pct * 100, 1),
            })
        return results

    # ---- FEATURE 2: DUE REMINDERS ----------------------------------------
    def due_reminders(self):
        """Filter interval_tracking() down to what actually needs attention,
        ranked most urgent first."""
        tracking = self.interval_tracking()
        due = [
            r for r in tracking
            if r["status"] in ("OVERDUE", "DUE SOON", "NEVER DONE")
        ]
        # NEVER DONE counts as maximum urgency (treat like 999%)
        due.sort(key=lambda r: r.get("urgency_pct", 999), reverse=True)
        return due

    # ---- FEATURE 3: COST HISTORY ------------------------------------------
    def cost_history(self):
        total_cost = sum(r.cost for r in self.records)
        by_type = Counter()
        for r in self.records:
            by_type[r.service_type] += r.cost

        avg_cost_per_service = round(total_cost / len(self.records), 2) if self.records else 0

        return {
            "total_cost": round(total_cost, 2),
            "total_services": len(self.records),
            "average_cost_per_service": avg_cost_per_service,
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
        }

    # ---- FEATURE 4: MILEAGE LOG SUMMARY -------------------------------------
    def mileage_summary(self):
        """
        Estimates how many km/day this vehicle is driven, using the
        earliest and latest known mileage readings from the service log
        plus the current odometer reading.
        """
        if not self.records:
            return {"entries": [], "avg_km_per_day": 0}

        entries = [
            {"date": r.service_date.isoformat(), "mileage": r.mileage}
            for r in self.records
        ]
        entries.append({"date": self.current_date.isoformat(), "mileage": self.current_mileage})

        first = self.records[0]
        span_days = (self.current_date - first.service_date).days
        span_km = self.current_mileage - first.mileage

        avg_km_per_day = round(span_km / span_days, 1) if span_days > 0 else 0

        return {
            "entries": entries,
            "avg_km_per_day": avg_km_per_day,
        }

    # ---- FEATURE 5: MAINTENANCE FORECAST ------------------------------------
    def maintenance_forecast(self):
        """
        Combines the usage rate (km/day) with each service's remaining
        km/time budget to PREDICT the calendar date each service will
        next be due — this is the "decision support" part: not just
        showing history, but projecting forward.
        """
        mileage_info = self.mileage_summary()
        km_per_day = mileage_info["avg_km_per_day"] or 20  # sane fallback if no history

        forecast = []
        for row in self.interval_tracking():
            service_type = row["service_type"]
            limits = SERVICE_INTERVALS[service_type]

            if row["last_done"] is None:
                forecast.append({
                    "service_type": service_type,
                    "predicted_due_date": "Unknown (no history) — schedule ASAP",
                    "km_remaining": None,
                })
                continue

            km_remaining = max(limits["km"] - row["km_since"], 0)
            days_remaining_by_km = km_remaining / km_per_day if km_per_day else 9999

            last_date = datetime.strptime(row["last_done"], "%Y-%m-%d").date()
            time_due_date = date.fromordinal(
                last_date.toordinal() + limits["months"] * 30
            )
            km_due_date = date.fromordinal(
                self.current_date.toordinal() + int(days_remaining_by_km)
            )

            # Whichever limit is reached FIRST wins (matches real-world rules)
            predicted_date = min(time_due_date, km_due_date)

            forecast.append({
                "service_type": service_type,
                "predicted_due_date": predicted_date.isoformat(),
                "km_remaining": km_remaining,
            })

        forecast.sort(key=lambda f: f["predicted_due_date"] or "")

        # Rough upcoming cost estimate: average historical cost per type,
        # applied to whichever services fall due in the next 90 days.
        cost = self.cost_history()
        upcoming_90_days = [
            f for f in forecast
            if f["predicted_due_date"] not in (None,)
            and not f["predicted_due_date"].startswith("Unknown")
            and (datetime.strptime(f["predicted_due_date"], "%Y-%m-%d").date() - self.current_date).days <= 90
        ]
        estimated_upcoming_cost = round(sum(
            cost["by_type"].get(f["service_type"], 0) for f in upcoming_90_days
        ), 2)

        return {
            "km_per_day_used": km_per_day,
            "forecast": forecast,
            "estimated_cost_next_90_days": estimated_upcoming_cost,
        }

    # ---- PUTTING IT ALL TOGETHER ---------------------------------------------
    def full_report(self):
        return {
            "records": [r.to_dict() for r in self.records],
            "interval_tracking": self.interval_tracking(),
            "due_reminders": self.due_reminders(),
            "cost_history": self.cost_history(),
            "mileage_summary": self.mileage_summary(),
            "maintenance_forecast": self.maintenance_forecast(),
        }
