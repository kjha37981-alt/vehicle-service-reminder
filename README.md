# Vehicle Service Reminder

A decision-support web app for vehicle maintenance — analyzes a service
log and generates recommendations (due reminders, forecasts) instead of
just storing records. Built with **Python (Flask)** + **HTML/CSS**.

## How to run it

1. Open this folder in VS Code.
2. Install Flask:
   ```
   pip install flask
   ```
   (use `py -m pip install flask` on Windows if `pip` isn't recognized)
3. Run the app:
   ```
   python app.py
   ```
4. Open `http://127.0.0.1:5000` in your browser.
5. Paste in `sample_service_log.txt` to try it, along with a current
   mileage higher than the last log entry (e.g. `18500`).

## Required input format

One service record per line, comma-separated:
```
Service Type, YYYY-MM-DD, mileage, cost
```
Example:
```
Oil Change, 2026-01-15, 12000, 1500
```

Recognized service types (edit `SERVICE_INTERVALS` in `analyzer.py` to
add more): Oil Change, Air Filter, Brake Pads, Tyre Rotation,
Battery Check, Coolant Flush, Timing Belt.

## Project structure

```
vehicle_reminder/
├── app.py                    # Flask routes
├── analyzer.py                 # All analysis logic
├── templates/
│   ├── index.html
│   └── results.html
├── static/style.css
└── sample_service_log.txt
```

## The 5 core features (in `analyzer.py`)

| Feature | Method | Idea |
|---|---|---|
| Service interval tracking | `interval_tracking()` | km/days since last service vs allowed limit |
| Due reminders | `due_reminders()` | filters + ranks urgent items |
| Cost history | `cost_history()` | totals, per-type breakdown, averages |
| Mileage log | `mileage_summary()` | estimates km/day usage rate |
| Maintenance forecast | `maintenance_forecast()` | projects next due DATE using usage rate |

## Key concepts to understand

- **`date` / `datetime` arithmetic** — `(current_date - last.service_date).days`
  gives elapsed days; used everywhere for "how overdue is this."
- **Whichever-limit-hits-first logic** — real service manuals define
  intervals as "X km OR Y months, whichever comes first." The code
  takes `max(km_pct, time_pct)` to model this correctly.
- **Forecasting** — instead of only reporting the past, `maintenance_forecast()`
  uses the vehicle's average km/day to *predict* a future due date. This
  is what makes it "decision support" rather than a record-keeper.
- **`Counter`** for grouping cost by service type — same technique as the
  Question Paper Analyzer project.
