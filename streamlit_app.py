import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="RedBus Analytics", layout="wide")
session = get_active_session()

st.title("🚌 RedBus Analytics Dashboard")

# KPIs
kpi = session.table("REDBUS_ANALYTICS.SEMANTIK.VW_KPI_SUMMARY").to_pandas()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Bookings", int(kpi["TOTAL_BOOKINGS"][0]))
col2.metric("Total Revenue", f"₹{kpi['TOTAL_REVENUE'][0]:,.0f}")
col3.metric("Net Revenue", f"₹{kpi['TOTAL_NET_REVENUE'][0]:,.0f}")
col4.metric("Avg Fare", f"₹{kpi['AVG_FARE'][0]:,.0f}")
col5.metric("Cancellation Rate", f"{kpi['CANCELLATION_RATE_PCT'][0]}%")

st.divider()

# Load detail data
df = session.table("REDBUS_ANALYTICS.SEMANTIK.VW_BOOKING_DETAILS").to_pandas()

# Filters
st.sidebar.header("Filters")
regions = st.sidebar.multiselect("Region", options=df["REGION"].unique(), default=list(df["REGION"].unique()))
operators = st.sidebar.multiselect("Operator", options=df["OPERATOR_NAME"].unique(), default=list(df["OPERATOR_NAME"].unique()))
status = st.sidebar.multiselect("Booking Status", options=df["BOOKING_STATUS"].unique(), default=list(df["BOOKING_STATUS"].unique()))

filtered = df[df["REGION"].isin(regions) & df["OPERATOR_NAME"].isin(operators) & df["BOOKING_STATUS"].isin(status)]

# Charts
c1, c2 = st.columns(2)
with c1:
    st.subheader("Revenue by Route")
    route_rev = filtered.groupby("ROUTE_NAME")["NET_AMOUNT"].sum().sort_values(ascending=False)
    st.bar_chart(route_rev)

with c2:
    st.subheader("Revenue by Operator")
    op_rev = filtered.groupby("OPERATOR_NAME")["NET_AMOUNT"].sum().sort_values(ascending=False)
    st.bar_chart(op_rev)

st.subheader("Booking Line Explorer")
st.dataframe(filtered, use_container_width=True)

st.divider()

c3, c4 = st.columns(2)

with c3:
    st.subheader("Bookings by Bus Type")
    bus_type_ct = filtered["BUS_TYPE"].value_counts()
    st.bar_chart(bus_type_ct)

with c4:
    st.subheader("Weekday vs Weekend Bookings")
    weekend_ct = filtered["JOURNEY_IS_WEEKEND"].map({True: "Weekend", False: "Weekday"}).value_counts()
    st.bar_chart(weekend_ct)

c5, c6 = st.columns(2)

with c5:
    st.subheader("Revenue by Customer Segment")
    seg_rev = filtered.groupby("CUSTOMER_SEGMENT")["NET_AMOUNT"].sum()
    st.bar_chart(seg_rev)

with c6:
    st.subheader("Booking Status Breakdown")
    status_ct = filtered["BOOKING_STATUS"].value_counts()
    st.bar_chart(status_ct)


st.divider()

c7, c8 = st.columns(2)

with c7:
    st.subheader("Occupancy % by Bus")
    occ = filtered.groupby(["BUS_ID", "SEAT_CAPACITY"])["PASSENGER_COUNT"].sum().reset_index()
    occ["OCCUPANCY_PCT"] = round(100 * occ["PASSENGER_COUNT"] / occ["SEAT_CAPACITY"], 1)
    st.bar_chart(occ.set_index("BUS_ID")["OCCUPANCY_PCT"])
    

with c8:
    st.subheader("Payment Mode Split")
    pay_ct = filtered["PAYMENT_MODE"].value_counts()
    st.bar_chart(pay_ct)

c9, c10 = st.columns(2)

with c9:
    st.subheader("Avg Discount % by Segment")
    disc_seg = filtered.groupby("CUSTOMER_SEGMENT")["DISCOUNT_PCT"].mean().round(1)
    st.bar_chart(disc_seg)

with c10:
    st.subheader("Top 5 Customers by Spend")
    top_cust = filtered.groupby("CUSTOMER_NAME")["NET_AMOUNT"].sum().sort_values(ascending=False).head(5)
    st.bar_chart(top_cust)

st.subheader("Revenue per KM by Route")
rev_per_km = (filtered.groupby("ROUTE_NAME").apply(
    lambda x: x["NET_AMOUNT"].sum() / x["DISTANCE_KM"].iloc[0]
)).sort_values(ascending=False)
st.bar_chart(rev_per_km)

st.divider()
st.header("📄 Ask a Policy Question")

user_question = st.text_input("Ask about cancellation, refunds, fares, or operator rules:")

if user_question:
    result = session.sql(
        "SELECT * FROM TABLE(REDBUS_ANALYTICS.SEMANTIK.SEARCH_POLICY(?))",
        params=[user_question]
    ).to_pandas()

    if len(result) > 0 and result["RELEVANCE"][0] > 0:
        st.success(f"**Answer (from: {result['TITLE'][0]})**")
        st.write(result["CONTENT"][0])
        st.caption(f"📌 Source: {result['DOC_ID'][0]} — {result['TITLE'][0]}")
    else:
        st.warning("Not available in indexed documents.")