import pandas as pd
from sqlalchemy import text
from src.config import logger
from src.db import engine, get_db_connection

class StarSchemaLoader:
    """Cleans staging data, applies transformations, and loads into the Star Schema."""

    def __init__(self):
        self.conn = get_db_connection()

    def _execute_sql_block(self, sql_block: str):
        """Helper to execute SQL containing one or more statements separated by semicolons."""
        statements = [stmt.strip() for stmt in sql_block.split(";") if stmt.strip()]
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

    def build_dim_category(self):
        """Populates dim_category with category names from CSV translation and API staging."""
        logger.info("Building dim_category...")
        sql = """
        DELETE FROM dim_category;

        INSERT OR IGNORE INTO dim_category (category_name, source_system)
        SELECT DISTINCT 
            COALESCE(LOWER(product_category_name_english), LOWER(product_category_name)) AS category_name,
            'CSV_BULK' AS source_system
        FROM staging_category_translation
        WHERE product_category_name IS NOT NULL

        UNION

        SELECT DISTINCT 
            LOWER(category) AS category_name,
            'LIVE_API' AS source_system
        FROM staging_api_products
        WHERE category IS NOT NULL

        UNION

        SELECT DISTINCT
            LOWER(product_category_name) AS category_name,
            'CSV_PRODUCTS' AS source_system
        FROM staging_products
        WHERE product_category_name IS NOT NULL;
        """
        self._execute_sql_block(sql)
        logger.info("dim_category successfully built.")

    def build_dim_products(self):
        """Populates dim_products unifying CSV products and live API catalog."""
        logger.info("Building dim_products...")
        sql = """
        DELETE FROM dim_products;

        -- 1. Load CSV Products translated to English categories
        INSERT INTO dim_products (product_id, title, category_name, price, stock, rating, brand, source_type)
        SELECT 
            sp.product_id,
            'Olist Product - ' || UPPER(SUBSTR(sp.product_id, 1, 8)) AS title,
            COALESCE(LOWER(t.product_category_name_english), LOWER(sp.product_category_name), 'Unknown') AS category_name,
            COALESCE(AVG(soi.price), 0.0) AS price,
            100 AS stock,
            4.0 AS rating,
            'Olist Seller Network' AS brand,
            'CSV_BULK' AS source_type
        FROM staging_products sp
        LEFT JOIN staging_category_translation t ON sp.product_category_name = t.product_category_name
        LEFT JOIN staging_order_items soi ON sp.product_id = soi.product_id
        GROUP BY sp.product_id;

        -- 2. Load Live API Products
        INSERT OR REPLACE INTO dim_products (product_id, title, category_name, price, stock, rating, brand, source_type)
        SELECT 
            'API_PROD_' || CAST(id AS TEXT) AS product_id,
            title,
            LOWER(category) AS category_name,
            price,
            COALESCE(stock, 0) AS stock,
            COALESCE(rating, 0.0) AS rating,
            COALESCE(brand, 'Generic') AS brand,
            'LIVE_API' AS source_type
        FROM staging_api_products
        WHERE id IS NOT NULL;
        """
        self._execute_sql_block(sql)
        logger.info("dim_products successfully built.")

    def build_dim_customers(self):
        """Populates dim_customers from staging_customers."""
        logger.info("Building dim_customers...")
        sql = """
        DELETE FROM dim_customers;

        INSERT INTO dim_customers (customer_id, customer_unique_id, city, state, zip_code)
        SELECT DISTINCT
            customer_id,
            customer_unique_id,
            customer_city,
            customer_state,
            CAST(customer_zip_code_prefix AS TEXT)
        FROM staging_customers
        WHERE customer_id IS NOT NULL;
        """
        self._execute_sql_block(sql)
        logger.info("dim_customers successfully built.")

    def build_dim_time(self):
        """Builds dim_time from purchase timestamps in staging_orders."""
        logger.info("Building dim_time...")
        # Get unique dates
        df_dates = pd.read_sql_query(
            "SELECT DISTINCT DATE(order_purchase_timestamp) as full_date FROM staging_orders WHERE order_purchase_timestamp IS NOT NULL AND order_purchase_timestamp != ''",
            self.conn
        )
        if df_dates.empty:
            logger.warning("No valid dates found in staging_orders for dim_time.")
            return

        df_dates['full_date'] = pd.to_datetime(df_dates['full_date'])
        df_dates = df_dates.sort_values('full_date').drop_duplicates().reset_index(drop=True)

        df_time = pd.DataFrame()
        df_time['full_date'] = df_dates['full_date'].dt.strftime('%Y-%m-%d')
        df_time['year'] = df_dates['full_date'].dt.year
        df_time['month'] = df_dates['full_date'].dt.month
        df_time['month_name'] = df_dates['full_date'].dt.strftime('%B')
        df_time['day'] = df_dates['full_date'].dt.day
        df_time['quarter'] = df_dates['full_date'].dt.quarter
        df_time['day_of_week'] = df_dates['full_date'].dt.strftime('%A')
        df_time['is_weekend'] = df_dates['full_date'].dt.dayofweek.isin([5, 6]).astype(int)

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM dim_time;"))
            df_time.to_sql('dim_time', con=conn, if_exists='append', index=False)
        logger.info(f"dim_time populated with {len(df_time)} unique date records.")

    def build_fact_orders(self) -> int:
        """Populates fact_orders by joining orders, items, products, reviews, and time dimensions."""
        logger.info("Building fact_orders...")
        sql = """
        DELETE FROM fact_orders;

        INSERT INTO fact_orders (
            order_id,
            product_id,
            customer_id,
            time_id,
            category_name,
            order_status,
            item_count,
            unit_price,
            freight_value,
            total_amount,
            review_score
        )
        SELECT 
            soi.order_id,
            soi.product_id,
            so.customer_id,
            dt.time_id,
            dp.category_name,
            so.order_status,
            COUNT(soi.order_item_id) AS item_count,
            soi.price AS unit_price,
            soi.freight_value,
            (soi.price * COUNT(soi.order_item_id)) + soi.freight_value AS total_amount,
            AVG(sr.review_score) AS review_score
        FROM staging_order_items soi
        JOIN staging_orders so ON soi.order_id = so.order_id
        LEFT JOIN dim_products dp ON soi.product_id = dp.product_id
        LEFT JOIN dim_time dt ON DATE(so.order_purchase_timestamp) = dt.full_date
        LEFT JOIN staging_reviews sr ON so.order_id = sr.order_id
        WHERE soi.order_id IS NOT NULL AND soi.product_id IS NOT NULL
        GROUP BY soi.order_id, soi.product_id;
        """
        self._execute_sql_block(sql)

        # Get count of fact rows loaded
        fact_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM fact_orders", self.conn).iloc[0]['cnt']
        logger.info(f"fact_orders built successfully with {fact_count:,} fact records.")
        return fact_count

    def run_all(self) -> int:
        self.build_dim_category()
        self.build_dim_products()
        self.build_dim_customers()
        self.build_dim_time()
        return self.build_fact_orders()

    def close(self):
        self.conn.close()
