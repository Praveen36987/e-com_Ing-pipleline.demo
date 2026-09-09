-- Analytical Views DDL

-- 1. Revenue by Category Over Time
DROP VIEW IF EXISTS view_revenue_by_category_over_time;
CREATE VIEW view_revenue_by_category_over_time AS
SELECT 
    f.category_name,
    t.year,
    t.month,
    t.month_name,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.item_count) AS total_items_sold,
    ROUND(SUM(f.total_amount), 2) AS total_revenue,
    ROUND(AVG(f.unit_price), 2) AS avg_item_price
FROM fact_orders f
LEFT JOIN dim_time t ON f.time_id = t.time_id
WHERE f.category_name IS NOT NULL AND f.category_name != 'Unknown'
GROUP BY f.category_name, t.year, t.month, t.month_name
ORDER BY t.year DESC, t.month DESC, total_revenue DESC;

-- 2. Conversion & Order Funnel Metrics
DROP VIEW IF EXISTS view_order_funnel_metrics;
CREATE VIEW view_order_funnel_metrics AS
WITH overall AS (
    SELECT COUNT(DISTINCT order_id) AS grand_total_orders FROM fact_orders
)
SELECT 
    f.order_status,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(COUNT(DISTINCT f.order_id) * 100.0 / NULLIF(o.grand_total_orders, 0), 2) AS pct_of_total_orders,
    ROUND(SUM(f.total_amount), 2) AS status_total_revenue,
    ROUND(AVG(f.total_amount), 2) AS avg_order_value
FROM fact_orders f
CROSS JOIN overall o
GROUP BY f.order_status, o.grand_total_orders
ORDER BY order_count DESC;

-- 3. Category Demand vs Catalog Size (Competition Proxy)
DROP VIEW IF EXISTS view_category_demand_vs_supply;
CREATE VIEW view_category_demand_vs_supply AS
SELECT 
    COALESCE(c.category_name, p.category_name) AS category_name,
    COUNT(DISTINCT p.product_id) AS catalog_product_count,
    COALESCE(SUM(f.item_count), 0) AS total_units_ordered,
    COALESCE(COUNT(DISTINCT f.order_id), 0) AS total_orders,
    ROUND(COALESCE(SUM(f.total_amount), 0.0), 2) AS total_revenue,
    ROUND(AVG(p.price), 2) AS avg_catalog_price
FROM dim_products p
LEFT JOIN dim_category c ON LOWER(p.category_name) = LOWER(c.category_name)
LEFT JOIN fact_orders f ON p.product_id = f.product_id
WHERE p.category_name IS NOT NULL AND p.category_name != 'Unknown'
GROUP BY COALESCE(c.category_name, p.category_name)
ORDER BY total_orders DESC;

-- 4. Review Sentiment vs Order Volume
DROP VIEW IF EXISTS view_sentiment_vs_volume;
CREATE VIEW view_sentiment_vs_volume AS
SELECT 
    f.category_name,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(f.review_score) AS reviewed_orders_count,
    ROUND(AVG(f.review_score), 2) AS avg_review_score,
    SUM(CASE WHEN f.review_score >= 4 THEN 1 ELSE 0 END) AS positive_reviews_count,
    SUM(CASE WHEN f.review_score <= 2 THEN 1 ELSE 0 END) AS negative_reviews_count,
    ROUND(SUM(CASE WHEN f.review_score >= 4 THEN 1.0 ELSE 0.0 END) * 100.0 / NULLIF(COUNT(f.review_score), 0), 2) AS positive_sentiment_pct,
    ROUND(SUM(f.total_amount), 2) AS total_revenue
FROM fact_orders f
WHERE f.category_name IS NOT NULL AND f.category_name != 'Unknown'
GROUP BY f.category_name
ORDER BY total_orders DESC;
