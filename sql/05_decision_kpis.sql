-- Decision-support scorecard.
-- This view ranks category-level actions from historical order behaviour. It is
-- intentionally an explainable KPI model, not an individual-customer predictor.

DROP VIEW IF EXISTS decision_category_scorecard;

CREATE VIEW decision_category_scorecard AS
WITH date_bounds AS (
    SELECT MAX(full_date) AS latest_date
    FROM dim_time
),
category_metrics AS (
    SELECT
        f.category_name,
        COUNT(DISTINCT f.order_id) AS total_orders,
        ROUND(SUM(f.total_amount), 2) AS total_revenue,
        COUNT(DISTINCT CASE WHEN f.order_status = 'delivered' THEN f.order_id END) AS delivered_orders,
        COUNT(DISTINCT CASE
            WHEN t.full_date > date(b.latest_date, '-90 day') THEN f.order_id
        END) AS recent_90d_orders,
        COUNT(DISTINCT CASE
            WHEN t.full_date > date(b.latest_date, '-180 day')
             AND t.full_date <= date(b.latest_date, '-90 day') THEN f.order_id
        END) AS prior_90d_orders,
        ROUND(AVG(f.review_score), 2) AS avg_review_score,
        ROUND(
            100.0 * SUM(CASE WHEN f.review_score >= 4 THEN 1 ELSE 0 END)
            / NULLIF(COUNT(f.review_score), 0),
            2
        ) AS positive_review_pct
    FROM fact_orders f
    JOIN dim_time t ON f.time_id = t.time_id
    CROSS JOIN date_bounds b
    WHERE f.category_name IS NOT NULL
      AND f.category_name NOT IN ('Unknown', '')
    GROUP BY f.category_name
),
catalog AS (
    SELECT category_name, COUNT(DISTINCT product_id) AS catalog_product_count
    FROM dim_products
    WHERE category_name IS NOT NULL
      AND category_name NOT IN ('Unknown', '')
    GROUP BY category_name
),
base AS (
    SELECT
        m.*,
        COALESCE(c.catalog_product_count, 0) AS catalog_product_count,
        ROUND(100.0 * m.delivered_orders / NULLIF(m.total_orders, 0), 2) AS fulfilment_rate_pct,
        ROUND(1.0 * m.total_orders / NULLIF(c.catalog_product_count, 0), 2) AS demand_to_competition_ratio,
        ROUND(
            100.0 * (m.recent_90d_orders - m.prior_90d_orders)
            / NULLIF(m.prior_90d_orders, 0),
            2
        ) AS order_growth_pct
    FROM category_metrics m
    LEFT JOIN catalog c ON c.category_name = m.category_name
),
scored AS (
    SELECT
        base.*,
        PERCENT_RANK() OVER (ORDER BY demand_to_competition_ratio) * 100 AS demand_score,
        PERCENT_RANK() OVER (ORDER BY total_revenue) * 100 AS revenue_score,
        PERCENT_RANK() OVER (ORDER BY COALESCE(order_growth_pct, -100)) * 100 AS momentum_score
    FROM base
)
SELECT
    category_name,
    total_orders,
    total_revenue,
    catalog_product_count,
    demand_to_competition_ratio,
    recent_90d_orders,
    prior_90d_orders,
    order_growth_pct,
    fulfilment_rate_pct,
    avg_review_score,
    positive_review_pct,
    ROUND(
        0.30 * demand_score
        + 0.25 * momentum_score
        + 0.20 * COALESCE(avg_review_score, 0) / 5.0 * 100
        + 0.15 * fulfilment_rate_pct
        + 0.10 * revenue_score,
        1
    ) AS decision_score,
    CASE
        WHEN fulfilment_rate_pct < 90 THEN 'FIX OPERATIONS: fulfilment is below 90%'
        WHEN COALESCE(avg_review_score, 0) < 3.5 THEN 'FIX CUSTOMER EXPERIENCE: low review score'
        WHEN demand_score >= 70 AND momentum_score >= 60 THEN 'INVEST: prioritise catalogue and marketing'
        WHEN demand_score >= 70 THEN 'TEST: demand is strong - validate growth before scaling'
        WHEN momentum_score >= 70 THEN 'WATCH: demand is accelerating - test a targeted campaign'
        ELSE 'MAINTAIN: monitor before allocating additional budget'
    END AS recommended_action
FROM scored
ORDER BY decision_score DESC, total_revenue DESC;
