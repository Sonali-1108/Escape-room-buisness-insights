# Escape Room Business Insights Dashboard

A Python PBL dashboard that analyses an Escape Room Management System SQLite database.

## Features
- Booking, paid revenue, group size and cancellation KPIs
- Filters for booking date, room theme and booking status
- Charts for themes, booking status, monthly paid revenue, room revenue, time slots and payment methods
- Room performance table and downloadable filtered CSV

## Files
- `app.py` — Streamlit dashboard
- `escape room.db` — the SQLite database supplied for the project
- `requirements.txt` — required Python libraries

## Run in VS Code
1. Install Python 3 if it is not already installed.
2. Open this folder in VS Code.
3. Open Terminal > New Terminal.
4. (Recommended) Create a virtual environment:
   - Windows: `py -m venv .venv`
   - Activate it: `.venv\Scripts\activate`
5. Install libraries:
   `python -m pip install -r requirements.txt`
6. Start the dashboard:
   `python -m streamlit run app.py`

Streamlit prints a local URL, usually `http://localhost:8501`, which you can open in your browser.

## Important data note
The provided database currently contains only seven bookings and seven payment records, so charts are a demonstration of the current data rather than statistically strong business trends. The dashboard counts revenue only from payments marked `Paid`, `Completed`, `Success`, or `Successful`; pending and refunded payments are not included.
