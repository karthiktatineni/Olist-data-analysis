"""
Olist E-Commerce Analytics Dashboard
====================================
Streamlit live interactive dashboard matching the 3 Power BI report pages:
- Page 1: Executive Overview
- Page 2: Sales & Product Performance
- Page 3: Orders, Delivery & Customer Insights
"""

import os
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# Page Configuration & Styling
# ==========================================
st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Clean & Business-focused CSS
st.markdown("""
<style>
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-title {
        color: #64748B;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #0F172A;
        font-size: 26px;
        font-weight: 700;
    }
    .stSelectbox label, .stDateInput label {
        font-weight: 600;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Direct Dataset Engine (data/processed/)
# ==========================================
@st.cache_data(ttl=3600)
def load_all_data():
    proc_dir = Path("data/processed")
    orders = pd.read_csv(proc_dir / "orders.csv")
    order_items = pd.read_csv(proc_dir / "order_items.csv")
    payments = pd.read_csv(proc_dir / "payments.csv")
    customers = pd.read_csv(proc_dir / "customers.csv")
    products = pd.read_csv(proc_dir / "products.csv")
    cat_trans = pd.read_csv(proc_dir / "category_translation.csv")
    sellers = pd.read_csv(proc_dir / "sellers.csv")
    
    # Datetime conversions
    for col in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors="coerce")
    
    orders["purchase_year_month"] = orders["order_purchase_timestamp"].dt.strftime("%Y-%m")
    orders["purchase_date"] = orders["order_purchase_timestamp"].dt.date
    
    # Delivery time calculation in days
    orders["delivery_time_days"] = (orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]).dt.total_seconds() / 86400.0
    
    # On-time delivery flag
    orders["is_on_time"] = (orders["order_status"] == "delivered") & (orders["order_delivered_customer_date"] <= orders["order_estimated_delivery_date"])
    
    # Merge category translation with products
    if "product_category_name_english" not in products.columns:
        products = products.merge(cat_trans, on="product_category_name", how="left")
    
    products["category_name"] = products["product_category_name_english"].fillna(products["product_category_name"]).fillna("Uncategorized")
    
    return orders, order_items, payments, customers, products, sellers

# Centered Animated Spinner & Loader
loader_placeholder = st.empty()
with loader_placeholder.container():
    st.markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px;">
        <div style="border: 5px solid #E2E8F0; border-top: 5px solid #2563EB; border-radius: 50%; width: 55px; height: 55px; animation: olistSpin 1s linear infinite;"></div>
        <h4 style="margin-top: 20px; font-weight: 600; color: #0F172A; letter-spacing: -0.3px;">Loading Olist E-Commerce Datasets...</h4>
        <p style="color: #64748B; font-size: 14px; margin-top: -6px;">Preparing analytics dashboards and metric cards. Please wait...</p>
    </div>
    <style>
        @keyframes olistSpin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)

orders_df, order_items_df, payments_df, customers_df, products_df, sellers_df = load_all_data()
loader_placeholder.empty()

# ==========================================
# Navigation Sidebar
# ==========================================
st.sidebar.title("🛒 Olist Analytics")
st.sidebar.caption("E-Commerce Performance Insights")
page = st.sidebar.radio(
    "Select Report Page:",
    [
        "Page 1: Executive Overview",
        "Page 2: Sales & Product Performance",
        "Page 3: Orders, Delivery & Customer Insights"
    ]
)

st.sidebar.markdown("---")

# ==============================================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# ==============================================================================
if page == "Page 1: Executive Overview":
    st.title("Executive Overview")
    st.markdown("Overall business performance, monthly trend, order status distribution, and top product categories.")

    # Sidebar Slicers
    st.sidebar.subheader("Page Filters")
    min_date = orders_df["purchase_date"].min()
    max_date = orders_df["purchase_date"].max()
    date_range = st.sidebar.date_input("Order Date Range", [min_date, max_date])
    
    status_options = ["All"] + sorted(orders_df["order_status"].dropna().unique().tolist())
    selected_status = st.sidebar.selectbox("Order Status", status_options)

    # Filter Data
    filt_orders = orders_df.copy()
    if len(date_range) == 2:
        filt_orders = filt_orders[(filt_orders["purchase_date"] >= date_range[0]) & (filt_orders["purchase_date"] <= date_range[1])]
    if selected_status != "All":
        filt_orders = filt_orders[filt_orders["order_status"] == selected_status]

    valid_order_ids = set(filt_orders["order_id"])
    filt_payments = payments_df[payments_df["order_id"].isin(valid_order_ids)]
    filt_order_items = order_items_df[order_items_df["order_id"].isin(valid_order_ids)]
    filt_customers = customers_df[customers_df["customer_id"].isin(filt_orders["customer_id"])]

    # 4 Top KPI Cards
    total_orders = filt_orders["order_id"].nunique()
    unique_cust = filt_customers["customer_unique_id"].nunique()
    total_payment = filt_payments["payment_value"].sum()
    avg_payment = total_payment / total_orders if total_orders > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Total Orders</div><div class="metric-value">{total_orders/1000:.2f}K</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Unique Customers</div><div class="metric-value">{unique_cust/1000:.2f}K</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Payment Value</div><div class="metric-value">R$ {total_payment/1e6:.2f}M</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Avg Payment / Order</div><div class="metric-value">R$ {avg_payment:.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visuals Row 1: Line Chart & Donut Chart
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.subheader("Monthly Order Trend")
        monthly_orders = filt_orders.groupby("purchase_year_month")["order_id"].nunique().reset_index()
        monthly_orders.columns = ["Month", "Orders"]
        fig_line = px.line(monthly_orders, x="Month", y="Orders", markers=True, color_discrete_sequence=["#2563EB"])
        fig_line.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=20, b=20, l=20, r=20), xaxis_tickangle=-45)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_right:
        st.subheader("Order Status Distribution")
        status_counts = filt_orders["order_status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_donut = px.pie(status_counts, names="Status", values="Count", hole=0.55, color_discrete_sequence=px.colors.qualitative.Prism)
        fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_donut, use_container_width=True)

    # Visuals Row 2: Top 10 Product Categories by Item Sales
    st.subheader("Top 10 Product Categories by Item Sales")
    items_prod = filt_order_items.merge(products_df[["product_id", "category_name"]], on="product_id", how="left")
    top_cat = items_prod.groupby("category_name")["price"].sum().reset_index()
    top_cat = top_cat.sort_values(by="price", ascending=False).head(10).sort_values(by="price", ascending=True)
    top_cat["Sales_Formatted"] = top_cat["price"].apply(lambda x: f"R$ {x/1e6:.2f}M" if x >= 1e6 else f"R$ {x/1e3:.1f}K")
    
    fig_bar = px.bar(top_cat, x="price", y="category_name", orientation="h", text="Sales_Formatted", color_discrete_sequence=["#0284C7"])
    fig_bar.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=20, l=20, r=20), xaxis_title="Total Item Sales (R$)", yaxis_title="")
    st.plotly_chart(fig_bar, use_container_width=True)


# ==============================================================================
# PAGE 2 — SALES & PRODUCT PERFORMANCE
# ==============================================================================
elif page == "Page 2: Sales & Product Performance":
    st.title("Sales & Product Performance")
    st.markdown("Identify which products, categories, and payment methods drive revenue.")

    # Sidebar Slicers
    st.sidebar.subheader("Page Filters")
    months = ["All"] + sorted(orders_df["purchase_year_month"].dropna().unique().tolist())
    selected_month = st.sidebar.selectbox("Filter Month", months)

    all_categories = ["All"] + sorted(products_df["category_name"].dropna().unique().tolist())
    selected_cat = st.sidebar.selectbox("Product Category", all_categories)

    # Filter Data
    filt_orders = orders_df.copy()
    if selected_month != "All":
        filt_orders = filt_orders[filt_orders["purchase_year_month"] == selected_month]

    valid_order_ids = set(filt_orders["order_id"])
    filt_items = order_items_df[order_items_df["order_id"].isin(valid_order_ids)].merge(
        products_df[["product_id", "category_name"]], on="product_id", how="left"
    )

    if selected_cat != "All":
        filt_items = filt_items[filt_items["category_name"] == selected_cat]
        cat_order_ids = set(filt_items["order_id"])
        filt_orders = filt_orders[filt_orders["order_id"].isin(cat_order_ids)]
        filt_payments = payments_df[payments_df["order_id"].isin(cat_order_ids)]
    else:
        filt_payments = payments_df[payments_df["order_id"].isin(valid_order_ids)]

    # 3 Top KPI Cards
    total_item_sales = filt_items["price"].sum()
    items_sold = len(filt_items)
    avg_item_price = total_item_sales / items_sold if items_sold > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Total Item Sales</div><div class="metric-value">R$ {total_item_sales/1e6:.2f}M</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Items Sold</div><div class="metric-value">{items_sold/1000:.2f}K</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Average Item Price</div><div class="metric-value">R$ {avg_item_price:.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visuals Row 1: Top 10 Categories Bar Chart & Monthly Payment Value
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Top 10 Categories by Item Sales")
        cat_sales = filt_items.groupby("category_name")["price"].sum().reset_index()
        top10_cat = cat_sales.sort_values(by="price", ascending=False).head(10).sort_values(by="price", ascending=True)
        fig_cat = px.bar(top10_cat, x="price", y="category_name", orientation="h", color_discrete_sequence=["#3B82F6"])
        fig_cat.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Sales (R$)", yaxis_title="")
        st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        st.subheader("Monthly Payment Value")
        pmt_orders = filt_payments.merge(orders_df[["order_id", "purchase_year_month"]], on="order_id", how="left")
        monthly_pmt = pmt_orders.groupby("purchase_year_month")["payment_value"].sum().reset_index()
        monthly_pmt.columns = ["Month", "Payment Value"]
        fig_pmt = px.line(monthly_pmt, x="Month", y="Payment Value", markers=True, color_discrete_sequence=["#10B981"])
        fig_pmt.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10), xaxis_tickangle=-45)
        st.plotly_chart(fig_pmt, use_container_width=True)

    # Visual 3: Payment Type Distribution
    st.subheader("Payment Type Distribution")
    pmt_type = filt_payments.groupby("payment_type")["payment_value"].sum().reset_index().sort_values(by="payment_value", ascending=False)
    pmt_type.columns = ["Payment Type", "Total Value"]
    pmt_type["Formatted"] = pmt_type["Total Value"].apply(lambda x: f"R$ {x/1e6:.2f}M")
    fig_pmt_type = px.bar(pmt_type, x="Payment Type", y="Total Value", text="Formatted", color="Payment Type", color_discrete_sequence=px.colors.qualitative.Safe)
    fig_pmt_type.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=20, l=20, r=20), yaxis_title="Total Value (R$)")
    st.plotly_chart(fig_pmt_type, use_container_width=True)


# ==============================================================================
# PAGE 3 — ORDERS, DELIVERY & CUSTOMER INSIGHTS
# ==============================================================================
else:
    st.title("Orders, Delivery & Customer Insights")
    st.markdown("Understand fulfillment performance, transit times, and customer geographical spread.")

    # Sidebar Slicers
    st.sidebar.subheader("Page Filters")
    status_list = ["All"] + sorted(orders_df["order_status"].dropna().unique().tolist())
    sel_status = st.sidebar.selectbox("Filter Status", status_list)

    states = ["All"] + sorted(customers_df["customer_state"].dropna().unique().tolist())
    sel_state = st.sidebar.selectbox("Customer State", states)

    months_p3 = ["All"] + sorted(orders_df["purchase_year_month"].dropna().unique().tolist())
    sel_month = st.sidebar.selectbox("Purchase Month", months_p3)

    # Filter Data
    filt_orders = orders_df.copy()
    if sel_status != "All":
        filt_orders = filt_orders[filt_orders["order_status"] == sel_status]
    if sel_month != "All":
        filt_orders = filt_orders[filt_orders["purchase_year_month"] == sel_month]

    filt_orders = filt_orders.merge(customers_df[["customer_id", "customer_state", "customer_unique_id"]], on="customer_id", how="left")
    if sel_state != "All":
        filt_orders = filt_orders[filt_orders["customer_state"] == sel_state]

    # 3 Top KPI Cards
    delivered_count = (filt_orders["order_status"] == "delivered").sum()
    cancelled_count = (filt_orders["order_status"] == "canceled").sum()
    
    delivered_subset = filt_orders[filt_orders["order_status"] == "delivered"]
    ontime_rate = (delivered_subset["is_on_time"].sum() / len(delivered_subset) * 100.0) if len(delivered_subset) > 0 else 0
    avg_delivery_days = delivered_subset["delivery_time_days"].mean() if len(delivered_subset) > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Delivered Orders</div><div class="metric-value">{delivered_count/1000:.2f}K</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Cancelled Orders</div><div class="metric-value">{cancelled_count:,}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">On-Time Delivery Rate</div><div class="metric-value">{ontime_rate:.1f}%</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Avg Delivery Time</div><div class="metric-value">{avg_delivery_days:.1f} Days</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visuals Row 1: Order Count by Status & Delivery Time Trend
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.subheader("Order Count by Status")
        status_df = filt_orders["order_status"].value_counts().reset_index()
        status_df.columns = ["Status", "Orders"]
        fig_st = px.bar(status_df, x="Status", y="Orders", color="Status", color_discrete_sequence=px.colors.qualitative.Bold)
        fig_st.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_st, use_container_width=True)

    with col_b:
        st.subheader("Average Delivery Time by Month (Days)")
        monthly_deliv = delivered_subset.groupby("purchase_year_month")["delivery_time_days"].mean().reset_index()
        monthly_deliv.columns = ["Month", "Avg Days"]
        fig_dt = px.line(monthly_deliv, x="Month", y="Avg Days", markers=True, color_discrete_sequence=["#E11D48"])
        fig_dt.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10), xaxis_tickangle=-45)
        st.plotly_chart(fig_dt, use_container_width=True)

    # Visuals Row 2: Orders by State & Top 10 States by Customer Count
    col_c, col_d = st.columns([1, 1])

    with col_c:
        st.subheader("Orders by Customer State")
        state_orders = filt_orders.groupby("customer_state")["order_id"].nunique().reset_index().sort_values(by="order_id", ascending=False).head(15)
        state_orders.columns = ["State", "Orders"]
        fig_so = px.bar(state_orders, x="State", y="Orders", color_discrete_sequence=["#6366F1"])
        fig_so.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_so, use_container_width=True)

    with col_d:
        st.subheader("Top 10 States by Customer Count")
        state_cust = filt_orders.groupby("customer_state")["customer_unique_id"].nunique().reset_index().sort_values(by="customer_unique_id", ascending=False).head(10)
        state_cust.columns = ["State", "Unique Customers"]
        fig_sc = px.bar(state_cust, x="State", y="Unique Customers", color_discrete_sequence=["#0EA5E9"])
        fig_sc.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_sc, use_container_width=True)
