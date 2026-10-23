import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Escape Room Business Insights", page_icon="🗝️", layout="wide")

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "escape room.db"

st.markdown("""
<style>
    .stApp { background: #f7f5ff; }
    h1, h2, h3 { color: #292044; }
    [data-testid="stMetric"] {
        background: white; padding: 16px; border-radius: 14px;
        border: 1px solid #e7e0fa;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗝️ Escape Room Business Insights Dashboard")
st.caption("Booking, room performance and payment analytics using your SQLite database.")

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH.name}. Put the database file in the same folder as app.py.")
    st.stop()

@st.cache_data
def load_data(db_path: str):
    with sqlite3.connect(db_path) as conn:
        bookings = pd.read_sql_query("""
            SELECT b.booking_id, b.booking_date, b.time_slot, b.group_size, b.status,
                   r.room_id, r.room_name, r.theme, r.capacity, r.price_per_person,
                   r.difficulty_level,
                   p.payment_id, p.amount, p.payment_date, p.payment_method, p.payment_status
            FROM Booking b
            LEFT JOIN Room r ON b.room_id = r.room_id
            LEFT JOIN Payment p ON b.booking_id = p.booking_id
        """, conn)
    bookings["booking_date"] = pd.to_datetime(bookings["booking_date"], errors="coerce")
    bookings["payment_date"] = pd.to_datetime(bookings["payment_date"], errors="coerce")
    bookings["group_size"] = pd.to_numeric(bookings["group_size"], errors="coerce").fillna(0)
    bookings["amount"] = pd.to_numeric(bookings["amount"], errors="coerce").fillna(0)
    for col in ["status", "payment_status", "theme", "room_name", "payment_method", "time_slot"]:
        bookings[col] = bookings[col].fillna("Unknown")
    return bookings

try:
    df = load_data(str(DB_PATH))
except Exception as exc:
    st.error("Could not read the database tables. Make sure this is the Escape Room SQLite database.")
    st.exception(exc)
    st.stop()

if df.empty:
    st.warning("Your database has no booking records yet.")
    st.stop()

st.sidebar.header("Dashboard Filters")
min_date = df["booking_date"].min()
max_date = df["booking_date"].max()
if pd.notna(min_date) and pd.notna(max_date):
    date_range = st.sidebar.date_input(
        "Booking date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        filtered = df[df["booking_date"].between(start_date, end_date)]
    else:
        filtered = df.copy()
else:
    filtered = df.copy()

themes = sorted(filtered["theme"].dropna().unique().tolist())
chosen_themes = st.sidebar.multiselect("Room theme", themes, default=themes)
statuses = sorted(filtered["status"].dropna().unique().tolist())
chosen_statuses = st.sidebar.multiselect("Booking status", statuses, default=statuses)
filtered = filtered[filtered["theme"].isin(chosen_themes) & filtered["status"].isin(chosen_statuses)]

if filtered.empty:
    st.info("No records match those filters. Change the filters in the sidebar.")
    st.stop()

paid = filtered[filtered["payment_status"].str.lower().isin(["paid", "completed", "success", "successful"])]
total_revenue = paid["amount"].sum()
total_bookings = filtered["booking_id"].nunique()
avg_group = filtered[["booking_id", "group_size"]].drop_duplicates()["group_size"].mean()
cancelled = filtered[filtered["status"].str.lower().eq("cancelled")]["booking_id"].nunique()
cancel_rate = (cancelled / total_bookings * 100) if total_bookings else 0
avg_payment = paid["amount"].mean() if not paid.empty else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Bookings", f"{total_bookings:,}")
m2.metric("Paid revenue", f"₹{total_revenue:,.0f}")
m3.metric("Avg. group size", f"{avg_group:.1f}" if pd.notna(avg_group) else "—")
m4.metric("Cancellation rate", f"{cancel_rate:.1f}%")
m5.metric("Avg. paid payment", f"₹{avg_payment:,.0f}")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Bookings by room theme")
    theme_counts = filtered.groupby("theme", as_index=False)["booking_id"].nunique().rename(columns={"booking_id": "Bookings"})
    fig = px.bar(theme_counts, x="theme", y="Bookings", color="theme", title="Number of bookings per theme")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Booking status")
    status_counts = filtered.groupby("status", as_index=False)["booking_id"].nunique().rename(columns={"booking_id": "Bookings"})
    fig = px.pie(status_counts, names="status", values="Bookings", hole=0.45, title="Booking status distribution")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Paid revenue over time")
    revenue_df = paid.dropna(subset=["payment_date"]).copy()
    if not revenue_df.empty:
        revenue_df["Month"] = revenue_df["payment_date"].dt.to_period("M").astype(str)
        monthly = revenue_df.groupby("Month", as_index=False)["amount"].sum().rename(columns={"amount": "Paid Revenue (₹)"})
        fig = px.line(monthly, x="Month", y="Paid Revenue (₹)", markers=True, title="Monthly paid revenue")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No paid payments with valid payment dates in this selection.")

with right:
    st.subheader("Paid revenue by room")
    room_revenue = paid.groupby("room_name", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    room_revenue = room_revenue.rename(columns={"amount": "Paid Revenue (₹)"})
    fig = px.bar(room_revenue, x="room_name", y="Paid Revenue (₹)", title="Revenue by room", color="Paid Revenue (₹)")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Popular time slots")
    slots = filtered.groupby("time_slot", as_index=False)["booking_id"].nunique().rename(columns={"booking_id": "Bookings"})
    fig = px.bar(slots, x="time_slot", y="Bookings", title="Bookings by time slot")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Payment methods")
    payment_df = filtered[filtered["payment_status"].str.lower().isin(["paid", "completed", "success", "successful"])]
    methods = payment_df.groupby("payment_method", as_index=False)["amount"].sum().rename(columns={"amount": "Paid Amount (₹)"})
    if not methods.empty:
        fig = px.bar(methods, x="payment_method", y="Paid Amount (₹)", title="Paid amount by payment method")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No paid payments for the selected filters.")

st.subheader("Room performance")
room_summary = filtered.groupby(["room_name", "theme", "difficulty_level"], as_index=False).agg(
    Bookings=("booking_id", "nunique"),
    Players=("group_size", "sum"),
    Paid_Revenue=("amount", lambda s: s[filtered.loc[s.index, "payment_status"].str.lower().isin(["paid", "completed", "success", "successful"])].sum())
).sort_values("Bookings", ascending=False)
room_summary = room_summary.rename(columns={"room_name": "Room", "theme": "Theme", "difficulty_level": "Difficulty", "Paid_Revenue": "Paid Revenue (₹)"})
st.dataframe(room_summary, use_container_width=True, hide_index=True)

st.subheader("Booking records")
display_df = filtered[[
    "booking_id", "booking_date", "room_name", "theme", "time_slot", "group_size",
    "status", "amount", "payment_method", "payment_status"
]].copy()
display_df["booking_date"] = display_df["booking_date"].dt.strftime("%Y-%m-%d")
display_df = display_df.rename(columns={
    "booking_id": "Booking ID", "booking_date": "Booking Date", "room_name": "Room",
    "theme": "Theme", "time_slot": "Time Slot", "group_size": "Group Size",
    "status": "Booking Status", "amount": "Payment Amount (₹)",
    "payment_method": "Payment Method", "payment_status": "Payment Status"
})
st.dataframe(display_df, use_container_width=True, hide_index=True)
st.download_button(
    "⬇️ Download filtered records as CSV",
    data=display_df.to_csv(index=False).encode("utf-8"),
    file_name="escape_room_filtered_bookings.csv",
    mime="text/csv"
)

st.caption("Revenue includes only payments marked Paid/Completed/Success. Results reflect the records currently stored in your database.")
