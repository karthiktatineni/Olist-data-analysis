-- =============================================================================
-- Olist E-Commerce Analytics SQL Layer
-- Database: olist_analytics
-- =============================================================================

USE olist_analytics;

-- -----------------------------------------------------------------------------
-- 1. Executive KPIs View
-- Summarizes high-level business performance metrics at a glance.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_executive_kpis AS
SELECT
    (SELECT COUNT(DISTINCT order_id) FROM orders) AS total_orders,
    (SELECT COUNT(DISTINCT customer_unique_id) FROM customers) AS unique_customers,
    (SELECT ROUND(SUM(payment_value), 2) FROM payments) AS total_payment_value,
    (SELECT ROUND(SUM(p.payment_value) / COUNT(DISTINCT o.order_id), 2) 
     FROM payments p JOIN orders o ON p.order_id = o.order_id) AS avg_payment_per_order,
    (SELECT ROUND(SUM(price), 2) FROM order_items) AS total_item_sales,
    (SELECT COUNT(*) FROM order_items) AS total_items_sold,
    (SELECT ROUND(AVG(price), 2) FROM order_items) AS avg_item_price,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'delivered') AS delivered_orders,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'canceled') AS canceled_orders,
    (SELECT ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) 
     FROM orders WHERE order_status = 'canceled') AS cancellation_rate_pct,
    (SELECT ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 1) 
     FROM orders 
     WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS avg_delivery_time_days,
    (SELECT ROUND(SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
     FROM orders 
     WHERE order_status = 'delivered' 
       AND order_delivered_customer_date IS NOT NULL 
       AND order_estimated_delivery_date IS NOT NULL) AS ontime_delivery_rate_pct;


-- -----------------------------------------------------------------------------
-- 2. Monthly Trend View (Orders, Payment Value, and Item Sales)
-- Pre-aggregates payments and items to avoid 1:M Cartesian multiplication.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_monthly_trends AS
SELECT
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_year_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(COALESCE(SUM(p.order_payment_value), 0), 2) AS total_payment_value,
    ROUND(COALESCE(SUM(i.order_item_sales), 0), 2) AS total_item_sales,
    COALESCE(SUM(i.items_sold), 0) AS total_items_sold,
    ROUND(AVG(
        CASE 
            WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL 
            THEN DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)
            ELSE NULL 
        END
    ), 1) AS avg_delivery_time_days
FROM orders o
LEFT JOIN (
    SELECT order_id, SUM(payment_value) AS order_payment_value
    FROM payments
    GROUP BY order_id
) p ON o.order_id = p.order_id
LEFT JOIN (
    SELECT order_id, SUM(price) AS order_item_sales, COUNT(*) AS items_sold
    FROM order_items
    GROUP BY order_id
) i ON o.order_id = i.order_id
WHERE o.order_purchase_timestamp IS NOT NULL
GROUP BY purchase_year_month
ORDER BY purchase_year_month;


-- -----------------------------------------------------------------------------
-- 3. Order Status Distribution View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_order_status_distribution AS
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS percentage_of_total
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;


-- -----------------------------------------------------------------------------
-- 4. Top Product Categories View (Item Sales & Volume)
-- Joins order_items with products and English category translations.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_top_product_categories AS
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name, 'Uncategorized') AS category_name,
    COUNT(oi.order_item_id) AS items_sold,
    ROUND(SUM(oi.price), 2) AS total_item_sales,
    ROUND(AVG(oi.price), 2) AS avg_item_price,
    ROUND(SUM(oi.freight_value), 2) AS total_freight_value
FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.product_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
GROUP BY category_name
ORDER BY total_item_sales DESC;


-- -----------------------------------------------------------------------------
-- 5. Payment Type Distribution View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_payment_type_distribution AS
SELECT
    payment_type,
    COUNT(*) AS transaction_count,
    ROUND(SUM(payment_value), 2) AS total_payment_value,
    ROUND(AVG(payment_value), 2) AS avg_payment_value,
    ROUND(SUM(payment_value) * 100.0 / (SELECT SUM(payment_value) FROM payments), 2) AS percentage_of_total
FROM payments
GROUP BY payment_type
ORDER BY total_payment_value DESC;


-- -----------------------------------------------------------------------------
-- 6. Delivery Performance View (Monthly & Fulfillment Metrics)
-- Excludes undelivered or missing dates from delivery-time calculations.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_delivery_performance AS
SELECT
    DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS purchase_year_month,
    COUNT(*) AS total_delivered_orders,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 1) AS avg_delivery_time_days,
    ROUND(AVG(DATEDIFF(order_estimated_delivery_date, order_purchase_timestamp)), 1) AS avg_estimated_delivery_days,
    SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) AS ontime_orders,
    SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS late_orders,
    ROUND(SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS ontime_delivery_rate_pct
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
GROUP BY purchase_year_month
ORDER BY purchase_year_month;


-- -----------------------------------------------------------------------------
-- 7. Geographic Insights View (Orders & Customers by State)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_geo_insights AS
SELECT
    c.customer_state,
    COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_state
ORDER BY total_orders DESC;
