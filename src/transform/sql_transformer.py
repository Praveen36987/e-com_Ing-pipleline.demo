import pandas as pd
from src.config import logger
from src.db import execute_sql_file, get_db_connection

class SQLTransformer:
    """Executes SQL analytical transformation scripts and provides dataframe interface to views."""

    def __init__(self):
        self.conn = get_db_connection()

    def create_views(self):
        """Executes DDL transformation files to build/refresh views."""
        logger.info("Executing transformation views DDL...")
        execute_sql_file("03_transformations.sql")
        execute_sql_file("04_seo_opportunity_report.sql")
        execute_sql_file("05_decision_kpis.sql")
        logger.info("All analytical views created successfully.")

    def get_seo_opportunity_report(self, limit: int = 20) -> pd.DataFrame:
        """Fetches top categories from seo_opportunity_report view."""
        query = f"SELECT * FROM seo_opportunity_report LIMIT {limit}"
        return pd.read_sql_query(query, self.conn)

    def get_revenue_by_category(self, limit: int = 15) -> pd.DataFrame:
        """Fetches category revenue over time."""
        query = f"SELECT * FROM view_revenue_by_category_over_time LIMIT {limit}"
        return pd.read_sql_query(query, self.conn)

    def get_order_funnel(self) -> pd.DataFrame:
        """Fetches order funnel metrics."""
        query = "SELECT * FROM view_order_funnel_metrics"
        return pd.read_sql_query(query, self.conn)

    def get_sentiment_vs_volume(self, limit: int = 15) -> pd.DataFrame:
        """Fetches review sentiment vs order volume."""
        query = f"SELECT * FROM view_sentiment_vs_volume LIMIT {limit}"
        return pd.read_sql_query(query, self.conn)

    def get_decision_scorecard(self, limit: int = 20) -> pd.DataFrame:
        """Fetch explainable category-level decision KPIs and recommended actions."""
        query = f"SELECT * FROM decision_category_scorecard LIMIT {limit}"
        return pd.read_sql_query(query, self.conn)

    def close(self):
        self.conn.close()
