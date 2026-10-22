# Olist E-Commerce Analytics Dashboard

An end-to-end e-commerce analytics project utilizing the **Olist Brazilian E-Commerce Public Dataset** (100k+ orders from 2016 to 2018). The project features a structured data processing pipeline, a relational **MySQL** database with a pre-aggregated **SQL Analytics Layer**, and interactive reporting across **Power BI** and **Streamlit**.

---

## Project Architecture

```
olist-analytics/
│
├── data/
│   ├── raw/                      # 9 original Kaggle CSV datasets
│   └── processed/                # 8 cleaned and validated CSV datasets
│
├── analysis.ipynb                # Data inspection, cleaning, EDA & visualizations
├── load_to_sql.py                # Automated migration script to MySQL database
├── analytics_views.sql           # SQL analytics layer (7 pre-aggregated views)
├── app.py                        # Streamlit 3-page interactive live dashboard
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation & execution guide
│
└── powerbi/
    ├── olist_analytics.pbix      # Power BI report file
    ├── powerbi_dax_and_model_guide.md # DAX measures & visual specs
    └── screenshots/              # Exported report screenshots
```

---

## 1. Database & SQL Analytics Layer

### Connection Details
* **Host**: `127.0.0.1` (or `localhost`)
* **Port**: `3306`
* **User**: `root`
* **Database**: `olist_analytics`

### Core Relational Tables
| Table | Rows | Primary Key | Description |
| :--- | :--- | :--- | :--- |
| **`customers`** | 99,441 | `customer_id` | Customer details, unique identifier, city, and state. |
| **`orders`** | 99,441 | `order_id` | Central fact table containing order status and fulfillment timestamps. |
| **`order_items`** | 112,650 | `(order_id, order_item_id)` | Line-item product purchases, item prices, freight costs, and seller IDs. |
| **`payments`** | 103,886 | `(order_id, payment_sequential)` | Payment method, installments, and monetary value recorded. |
| **`products`** | 32,951 | `product_id` | Product physical dimensions, weight, and category name. |
| **`sellers`** | 3,095 | `seller_id` | Seller location (zip code, city, state). |
| **`reviews`** | 99,224 | `review_id` | Customer review score (1-5), comments, and response timestamps. |
| **`category_translation`** | 71 | `product_category_name` | Portuguese-to-English translation mapping for categories. |

### Analytics SQL Views ([analytics_views.sql](file:///c:/Users/karth/Desktop/proj/analytics_views.sql))
To avoid Cartesian explosion (fan-out) across one-to-many joins, dedicated views pre-aggregate child tables before joining:

1. **`view_executive_kpis`**: Single-row summary of top-level metrics (Total Orders, Customers, Payment Value, Delivery Times, On-time Rate).
2. **`view_monthly_trends`**: Monthly grain breakdown of order volume, payment value, item sales, and average delivery transit times.
3. **`view_order_status_distribution`**: Total counts and proportions for each order status (`delivered`, `shipped`, `canceled`, etc.).
4. **`view_top_product_categories`**: Product sales ranking by item price sum (`order_items.price`) and item counts using English translations.
5. **`view_payment_type_distribution`**: Revenue and transaction share split across payment types (Credit Card, Boleto, Voucher, Debit Card).
6. **`view_delivery_performance`**: Monthly fulfillment metrics, comparing actual delivery days to promised estimated delivery dates.
7. **`view_geo_insights`**: Geographic customer and order concentrations across Brazilian states (`SP`, `RJ`, `MG`, etc.).

---

## 2. Power BI Data Model & Measures

### Relationships (Star Schema)
* `customers[customer_id]` (1) &rarr; (Many) `orders[customer_id]`
* `orders[order_id]` (1) &rarr; (Many) `order_items[order_id]`
* `orders[order_id]` (1) &rarr; (Many) `payments[order_id]`
* `orders[order_id]` (1) &rarr; (Many) `reviews[order_id]`
* `products[product_id]` (1) &rarr; (Many) `order_items[product_id]`
* `sellers[seller_id]` (1) &rarr; (Many) `order_items[seller_id]`
* `category_translation[product_category_name]` (1) &rarr; (Many) `products[product_category_name]`

### DAX Measures
All measures are grouped in a dedicated `_Measures` table:

```dax
-- Executive KPIs
Total Orders = DISTINCTCOUNT(orders[order_id])
Unique Customers = DISTINCTCOUNT(customers[customer_unique_id])
Total Payment Value = SUM(payments[payment_value])
Average Payment Per Order = DIVIDE([Total Payment Value], [Total Orders], 0)

-- Sales & Product Performance
Total Item Sales = SUM(order_items[price])
Items Sold = COUNTROWS(order_items)
Average Item Price = DIVIDE([Total Item Sales], [Items Sold], 0)

-- Delivery & Fulfillment
Delivered Orders = CALCULATE([Total Orders], orders[order_status] = "delivered")
Cancelled Orders = CALCULATE([Total Orders], orders[order_status] = "canceled")
Cancellation Rate = DIVIDE([Cancelled Orders], [Total Orders], 0)
Average Delivery Time Days = AVERAGE(orders[delivery_time_days])
On-Time Delivery Rate = DIVIDE(CALCULATE([Delivered Orders], orders[is_on_time] = 1), [Delivered Orders], 0)
```

---

## 3. Power BI Report Pages

### Page 1 — Executive Overview
* **Audience**: C-Suite / Operations Managers
* **4 Top KPI Cards**:
  * Total Orders: **99.44K**
  * Unique Customers: **96.10K**
  * Total Payment Value: **R$ 16.01M**
  * Avg Payment / Order: **R$ 160.99**
* **Line Chart**: Monthly Order Trend (`orders[purchase_year_month]` vs `[Total Orders]`)
* **Line Chart**: Monthly Payment Value (`orders[purchase_year_month]` vs `[Total Payment Value]`)
* **Donut Chart**: Order Status Distribution (`orders[order_status]`)
* **Bar Chart**: Top 10 Product Categories by Item Sales (`category_translation[product_category_name_english]` vs `[Total Item Sales]`)
* **Slicers**: Date range slider (`orders[order_purchase_timestamp]`) and Order Status dropdown.

### Page 2 — Sales & Product Performance
* **Audience**: Merchandising & Category Managers
* **3 Top KPI Cards**:
  * Total Item Sales: **R$ 13.59M**
  * Items Sold: **112.65K**
  * Average Item Price: **R$ 120.65**
* **Horizontal Bar Chart**: Top 10 Product Categories by Item Sales
* **Line Chart**: Monthly Payment Value trend
* **Column Chart**: Payment Type Breakdown (Credit Card, Boleto, Voucher, Debit Card)
* **Slicers**: Month and Product Category.

### Page 3 — Orders, Delivery & Customer Insights
* **Audience**: Logistics & Customer Experience Managers
* **4 Top KPI Cards**:
  * Delivered Orders: **96.48K**
  * Cancelled Orders: **625** (Cancellation Rate: **0.63%**)
  * On-Time Delivery Rate: **91.9%**
  * Avg Delivery Time: **12.5 Days**
* **Bar Chart**: Order count by status
* **Line Chart**: Average delivery time trend by month
* **Bar Charts**: Total Orders by Customer State & Unique Customers by State
* **Slicers**: Order status, purchase month, and customer state.

---

## 4. Live Streamlit Application

An interactive web dashboard matching the exact 3-page Power BI specification is available via Streamlit:

```bash
# Run local dashboard
streamlit run app.py
```

* **Live Data**: Queries the local MySQL database directly via SQLAlchemy.
* **Interactive Filtering**: Real-time multi-select and date range slicing using Plotly charts.
* **Zero Latency**: Implements caching for sub-second page transitions.

---

## 5. How to Connect Power BI to MySQL

1. Open **Power BI Desktop**.
2. Select **Get Data** &rarr; **More...** &rarr; search for **MySQL database** &rarr; click **Connect**.
3. In the dialog:
   * **Server**: `127.0.0.1:3306`
   * **Database**: `olist_analytics`
   * **Connectivity mode**: `Import`
4. Enter credentials under the **Database** tab:
   * **User name**: `root`
   * **Password**: `NewPassword@123`
5. Select the 8 base tables (or the 7 pre-built views from `analytics_views.sql`) and click **Load**.
6. Build or verify the visuals as outlined in [powerbi_dax_and_model_guide.md](file:///c:/Users/karth/Desktop/proj/powerbi/powerbi_dax_and_model_guide.md) and save the report as `powerbi/olist_analytics.pbix`.
