-- SEO Opportunity Report View DDL

DROP VIEW IF EXISTS seo_opportunity_report;

CREATE VIEW seo_opportunity_report AS
WITH category_metrics AS (
    SELECT 
        p.category_name,
        COUNT(DISTINCT p.product_id) AS catalog_product_count,
        COALESCE(COUNT(DISTINCT f.order_id), 0) AS total_orders,
        COALESCE(SUM(f.item_count), 0) AS total_units_sold,
        ROUND(COALESCE(SUM(f.total_amount), 0.0), 2) AS total_revenue,
        ROUND(AVG(p.price), 2) AS avg_product_price,
        ROUND(AVG(f.review_score), 2) AS avg_review_score
    FROM dim_products p
    LEFT JOIN fact_orders f ON p.product_id = f.product_id
    WHERE p.category_name IS NOT NULL 
      AND p.category_name != 'Unknown'
      AND p.category_name != ''
    GROUP BY p.category_name
)
SELECT 
    category_name,
    total_orders,
    total_revenue,
    catalog_product_count,
    avg_product_price,
    avg_review_score,
    ROUND(total_orders * 1.0 / NULLIF(catalog_product_count, 0), 2) AS demand_to_competition_ratio,
    RANK() OVER (
        ORDER BY (total_orders * 1.0 / NULLIF(catalog_product_count, 0)) DESC, total_revenue DESC
    ) AS opportunity_rank,
    CASE 
        WHEN (total_orders * 1.0 / NULLIF(catalog_product_count, 0)) >= 50.0 THEN 'PRIME TARGET: High Demand, Low Catalog Saturation'
        WHEN (total_orders * 1.0 / NULLIF(catalog_product_count, 0)) >= 10.0 THEN 'STRONG OPPORTUNITY: solid order volume per product'
        WHEN (total_orders * 1.0 / NULLIF(catalog_product_count, 0)) >= 2.0  THEN 'MODERATE: Balanced demand and competition'
        ELSE 'SATURATED / LOW DEMAND: High product competition relative to orders'
    END AS seo_strategy_recommendation
FROM category_metrics
ORDER BY opportunity_rank ASC;
