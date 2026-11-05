"""
Streamlit dashboard for the event venue analytics project.

Run:
    streamlit run dashboard/app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/eventdb")

st.set_page_config(page_title="Event Venue Analytics", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


@st.cache_data(ttl=600)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine(), params=params)


# ------------------------------------------------------------------ filters
years = query("SELECT DISTINCT EXTRACT(YEAR FROM start_date)::int AS y FROM events ORDER BY 1")["y"].tolist()
types = query("SELECT name FROM event_types ORDER BY name")["name"].tolist()

st.sidebar.header("Filters")
sel_years = st.sidebar.multiselect("Year", years, default=years)
sel_types = st.sidebar.multiselect("Event type", types, default=types)

if not sel_years or not sel_types:
    st.warning("Select at least one year and one event type.")
    st.stop()

df = query(
    """
    SELECT *, EXTRACT(YEAR FROM start_date)::int AS year,
              EXTRACT(MONTH FROM start_date)::int AS month
    FROM v_event_financials
    WHERE EXTRACT(YEAR FROM start_date)::int = ANY(%(years)s)
      AND event_type = ANY(%(types)s)
    """,
    {"years": sel_years, "types": sel_types},
)
done = df[df["status"] == "completed"]

# ------------------------------------------------------------------ KPIs
st.title("Event Venue Analytics")
st.caption("Synthetic data for a fictional congress center, 2023–2025")

k1, k2, k3, k4, k5 = st.columns(5)
revenue = done["total_revenue"].sum()
k1.metric("Revenue", f"€{revenue / 1e6:,.1f} M")
k2.metric("Gross margin", f"{done['gross_margin'].sum() / revenue * 100:.1f} %" if revenue else "–")
k3.metric("Events", f"{len(done):,}")
k4.metric("Cancellation rate", f"{(df['status'] == 'cancelled').mean() * 100:.1f} %")
k5.metric("Show-up rate", f"{(done['actual_attendees'].sum() / done['expected_attendees'].sum()) * 100:.1f} %")

st.divider()

# ------------------------------------------------------------------ row 1
c1, c2 = st.columns(2)

with c1:
    st.subheader("Revenue by event type")
    by_type = (done.groupby("event_type", as_index=False)
                   .agg(revenue=("total_revenue", "sum"), margin=("gross_margin", "sum"))
                   .sort_values("revenue"))
    fig = px.bar(by_type, x="revenue", y="event_type", orientation="h",
                 labels={"revenue": "Revenue (€)", "event_type": ""})
    st.plotly_chart(fig, width="stretch")

with c2:
    st.subheader("Seasonality – revenue per month")
    by_month = (done.groupby(["year", "month"], as_index=False)["total_revenue"].sum())
    by_month["year"] = by_month["year"].astype(str)
    fig = px.line(by_month, x="month", y="total_revenue", color="year", markers=True,
                  labels={"total_revenue": "Revenue (€)", "month": "Month"})
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ row 2
c3, c4 = st.columns(2)

with c3:
    st.subheader("Room utilization")
    util = query(
        """
        WITH booked AS (
            SELECT er.room_id, SUM(er.days) AS days
            FROM event_rooms er
            JOIN events e       ON e.event_id = er.event_id
            JOIN event_types et ON et.event_type_id = e.event_type_id
            WHERE EXTRACT(YEAR FROM e.start_date)::int = ANY(%(years)s)
              AND et.name = ANY(%(types)s)
            GROUP BY er.room_id
        )
        SELECT r.room_name,
               ROUND(COALESCE(b.days, 0) * 100.0 / (365 * %(n)s), 1) AS utilization_pct
        FROM rooms r
        LEFT JOIN booked b ON b.room_id = r.room_id
        ORDER BY utilization_pct
        """,
        {"years": sel_years, "types": sel_types, "n": len(sel_years)},
    )
    fig = px.bar(util, x="utilization_pct", y="room_name", orientation="h",
                 labels={"utilization_pct": "Booked days (%)", "room_name": ""})
    st.plotly_chart(fig, width="stretch")

with c4:
    st.subheader("Cancellation rate by lead time")
    bins = [0, 60, 180, 365, 10_000]
    labels = ["< 2 months", "2–6 months", "6–12 months", "> 12 months"]
    tmp = df.assign(lead=pd.cut(df["lead_time_days"], bins=bins, labels=labels, right=False))
    canc = (tmp.groupby("lead", observed=False)["status"]
               .apply(lambda s: (s == "cancelled").mean() * 100)
               .reset_index(name="cancel_rate_pct"))
    fig = px.bar(canc, x="lead", y="cancel_rate_pct",
                 labels={"lead": "Booked ... before the event", "cancel_rate_pct": "Cancelled (%)"})
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ row 3
st.subheader("Top 10 customers")
top = (done.groupby(["company_name", "customer_type"], as_index=False)
           .agg(events=("event_id", "count"), revenue=("total_revenue", "sum"))
           .sort_values("revenue", ascending=False)
           .head(10))
top["share_of_revenue_%"] = (top["revenue"] / revenue * 100).round(1)
top["revenue"] = top["revenue"].round(0)
st.dataframe(top, hide_index=True, width="stretch")
