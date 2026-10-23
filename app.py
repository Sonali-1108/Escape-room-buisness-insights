
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Escape Room | Business Insights",
    page_icon="🗝️",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "escape room.db"

# Pastel colour palette
LAVENDER = "#9B8BC2"
BLUE = "#91AFCF"
SAGE = "#91B7A5"
ROSE = "#C99BAF"
PLUM = "#75658F"
PALETTE = [LAVENDER, BLUE, SAGE, ROSE, PLUM]

st.markdown("""
<style>
.stApp {
    background-color: #F8F7FB;
}
[data-testid="stSidebar"] {
    background-color: #EEE9F6;
}
h1, h2, h3 {
    color: #30283D;
}
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E6DFF0;
    padding: 18px;
    border-radius: 14px;
}
[data-testid="stMetricLabel"] {
    color: #716780;
}
[data-testid="stMetricValue"] {
    color: #51416F;
}
div[data-baseweb="select"] > div {
    border-radius: 9px;
}
</style>
""", unsafe_allow_html=True)

st.title("🗝️ Escape Room Business Insights")

if not DB_PATH.exists():
    st.error("Database not found. Keep 'escape room.db' beside app.py.")
    st.stop()


@st.cache_data
def load_data(db_path):
    with sqlite3.connect(db_path) as conn:
        data = pd.read_sql_query("""
            SELECT
                b.booking_id, b.booking_date, b.time_slot,
                b.group_size, b.status,
                r.room_id, r.room_name, r.theme,
                r.capacity, r.price_per_person,
                r.difficulty_level,
                p.payment_id, p.amount, p.payment_date,
                p.payment_method, p.payment_status
            FROM Booking b
            LEFT JOIN Room r ON b.room_id = r.room_id
            LEFT JOIN Payment p ON b.booking_id = p.booking_id
        """, conn)

    data["booking_date"] = pd.to_datetime(
        data["booking_date"], errors="coerce"
    )
    data["payment_date"] = pd.to_datetime(
        data["payment_date"], errors="coerce"
    )

    for col in ["group_size", "amount"]:
        data[col] = pd.to_numeric(
            data[col], errors="coerce"
        ).fillna(0)

    for col in [
        "status", "payment_status", "theme", "room_name",
        "payment_method", "time_slot", "difficulty_level"
    ]:
        data[col] = data[col].fillna("Unknown")

    data["Paid Amount"] = data["amount"].where(
        data["payment_status"].str.lower().isin(
            ["paid", "completed", "success", "successful"]
        ),
        0
    )
    return data


try:
    df = load_data(str(DB_PATH))
except Exception as exc:
    st.error("Could not read the database. Check your SQLite tables.")
    st.exception(exc)
    st.stop()

if df.empty:
    st.warning("No booking records found in the database.")
    st.stop()

# Sidebar navigation
st.sidebar.title("🗝️ Escape Room")
st.sidebar.caption("BUSINESS INSIGHTS")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Overview",
        "Booking Analytics",
        "Room Performance",
        "Payment Analytics",
        "Booking Records"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("Filters")

min_date = df["booking_date"].min()
max_date = df["booking_date"].max()

filtered = df.copy()

if pd.notna(min_date) and pd.notna(max_date):
    date_range = st.sidebar.date_input(
        "Booking date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        filtered = filtered[
            (filtered["booking_date"] >= start)
            & (filtered["booking_date"] < end)
        ]

themes = sorted(filtered["theme"].unique().tolist())
chosen_themes = st.sidebar.multiselect(
    "Room theme", themes, default=themes
)

statuses = sorted(filtered["status"].unique().tolist())
chosen_statuses = st.sidebar.multiselect(
    "Booking status", statuses, default=statuses
)

filtered = filtered[
    filtered["theme"].isin(chosen_themes)
    & filtered["status"].isin(chosen_statuses)
]

if filtered.empty:
    st.warning("No records match these filters. Change the sidebar filters.")
    st.stop()

# Chart styling
def style_chart(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#443B52"),
        title_font=dict(color="#443B52"),
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text=""
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEEAF3")
    return fig


paid = filtered[filtered["Paid Amount"] > 0]
total_bookings = filtered["booking_id"].nunique()
total_revenue = filtered["Paid Amount"].sum()

unique_bookings = filtered.drop_duplicates("booking_id")
avg_group = unique_bookings["group_size"].mean()

cancelled = unique_bookings[
    unique_bookings["status"].str.lower() == "cancelled"
]["booking_id"].nunique()

cancel_rate = (
    cancelled / total_bookings * 100 if total_bookings else 0
)

avg_payment = paid["Paid Amount"].mean() if not paid.empty else 0


def show_metrics():
    a, b, c, d = st.columns(4)
    a.metric("Total Bookings", f"{total_bookings:,}")
    b.metric("Paid Revenue", f"₹{total_revenue:,.0f}")
    c.metric(
        "Average Group Size",
        f"{avg_group:.1f}" if pd.notna(avg_group) else "—"
    )
    d.metric("Cancellation Rate", f"{cancel_rate:.1f}%")


# PAGE 1: OVERVIEW
if page == "Overview":
    st.subheader("Business Overview")
    show_metrics()

    left, right = st.columns(2)

    with left:
        theme_counts = (
            filtered.groupby("theme", as_index=False)
            .agg(Bookings=("booking_id", "nunique"))
        )
        fig = px.bar(
            theme_counts,
            x="theme",
            y="Bookings",
            color="theme",
            color_discrete_sequence=PALETTE,
            title="Bookings by Room Theme"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    with right:
        status_counts = (
            filtered.groupby("status", as_index=False)
            .agg(Bookings=("booking_id", "nunique"))
        )
        fig = px.pie(
            status_counts,
            names="status",
            values="Bookings",
            hole=0.5,
            color_discrete_sequence=PALETTE,
            title="Booking Status Distribution"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    st.subheader("Revenue Snapshot")
    st.metric("Average Paid Payment", f"₹{avg_payment:,.0f}")


# PAGE 2: BOOKING ANALYTICS
elif page == "Booking Analytics":
    st.subheader("Booking Analytics")
    st.caption("Explore booking patterns, status and preferred time slots.")

    a, b = st.columns(2)

    with a:
        daily = (
            filtered.dropna(subset=["booking_date"])
            .groupby("booking_date", as_index=False)
            .agg(Bookings=("booking_id", "nunique"))
        )
        fig = px.line(
            daily,
            x="booking_date",
            y="Bookings",
            markers=True,
            title="Bookings Over Time",
            color_discrete_sequence=[LAVENDER]
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    with b:
        statuses_df = (
            filtered.groupby("status", as_index=False)
            .agg(Bookings=("booking_id", "nunique"))
        )
        fig = px.bar(
            statuses_df,
            x="status",
            y="Bookings",
            color="status",
            color_discrete_sequence=PALETTE,
            title="Bookings by Status"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    slots = (
        filtered.groupby("time_slot", as_index=False)
        .agg(Bookings=("booking_id", "nunique"))
        .sort_values("Bookings", ascending=False)
    )
    fig = px.bar(
        slots,
        x="time_slot",
        y="Bookings",
        color_discrete_sequence=[BLUE],
        title="Popular Time Slots"
    )
    st.plotly_chart(style_chart(fig), use_container_width=True)


# PAGE 3: ROOM PERFORMANCE
elif page == "Room Performance":
    st.subheader("Room Performance")
    st.caption("Compare room popularity, player traffic and paid revenue.")

    room_summary = (
        filtered.groupby(
            ["room_name", "theme", "difficulty_level"],
            as_index=False
        )
        .agg(
            Bookings=("booking_id", "nunique"),
            Players=("group_size", "sum"),
            **{"Paid Revenue (₹)": ("Paid Amount", "sum")}
        )
        .sort_values("Bookings", ascending=False)
    )

    a, b = st.columns(2)

    with a:
        fig = px.bar(
            room_summary,
            x="room_name",
            y="Bookings",
            color_discrete_sequence=[LAVENDER],
            title="Bookings by Room"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    with b:
        fig = px.bar(
            room_summary,
            x="room_name",
            y="Paid Revenue (₹)",
            color_discrete_sequence=[SAGE],
            title="Paid Revenue by Room"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    st.subheader("Room Summary")
    st.dataframe(room_summary, use_container_width=True, hide_index=True)


# PAGE 4: PAYMENT ANALYTICS
elif page == "Payment Analytics":
    st.subheader("Payment Analytics")
    st.caption("Review collected revenue, payment status and payment methods.")

    a, b = st.columns(2)

    with a:
        payment_status = (
            filtered.groupby("payment_status", as_index=False)
            .agg(Payments=("payment_id", "count"))
        )
        fig = px.pie(
            payment_status,
            names="payment_status",
            values="Payments",
            hole=0.5,
            color_discrete_sequence=PALETTE,
            title="Payment Status Distribution"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    with b:
        methods = (
            filtered.groupby("payment_method", as_index=False)
            .agg(**{"Paid Amount (₹)": ("Paid Amount", "sum")})
        )
        fig = px.bar(
            methods,
            x="payment_method",
            y="Paid Amount (₹)",
            color_discrete_sequence=[BLUE],
            title="Paid Amount by Payment Method"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    revenue_df = paid.dropna(subset=["payment_date"]).copy()

    if not revenue_df.empty:
        revenue_df["Month"] = (
            revenue_df["payment_date"].dt.to_period("M").astype(str)
        )
        monthly = (
            revenue_df.groupby("Month", as_index=False)
            .agg(**{"Paid Revenue (₹)": ("Paid Amount", "sum")})
        )
        fig = px.line(
            monthly,
            x="Month",
            y="Paid Revenue (₹)",
            markers=True,
            color_discrete_sequence=[PLUM],
            title="Paid Revenue Over Time"
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)
    else:
        st.info("No valid payment dates for the selected filters.")


# PAGE 5: BOOKING RECORDS
elif page == "Booking Records":
    st.subheader("Booking Records")
    st.caption("Browse booking and payment details.")

    display_df = filtered[
        [
            "booking_id", "booking_date", "room_name", "theme",
            "time_slot", "group_size", "status", "amount",
            "payment_method", "payment_status"
        ]
    ].copy()

    display_df["booking_date"] = (
        display_df["booking_date"].dt.strftime("%Y-%m-%d")
    )

    display_df = display_df.rename(columns={
        "booking_id": "Booking ID",
        "booking_date": "Booking Date",
        "room_name": "Room",
        "theme": "Theme",
        "time_slot": "Time Slot",
        "group_size": "Group Size",
        "status": "Booking Status",
        "amount": "Payment Amount (₹)",
        "payment_method": "Payment Method",
        "payment_status": "Payment Status"
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
