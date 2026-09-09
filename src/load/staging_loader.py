import json
import pandas as pd
import sqlite3
from typing import Dict, Tuple
from sqlalchemy import text
from src.config import logger
from src.db import engine, get_db_connection

class StagingLoader:
    """Validates raw extracted data and loads into staging and rejects tables."""

    def __init__(self):
        self.conn = get_db_connection()

    def log_rejects(self, source_table: str, rejected_df: pd.DataFrame, reason: str) -> int:
        """Writes invalid/corrupt rows to the rejects table with reason logged as JSON."""
        if rejected_df.empty:
            return 0
        
        reject_records = []
        for _, row in rejected_df.iterrows():
            row_dict = row.to_dict()
            # Convert non-serializable objects if any
            clean_dict = {k: (str(v) if pd.notna(v) else None) for k, v in row_dict.items()}
            reject_records.append({
                "source_table": source_table,
                "rejected_row_data": json.dumps(clean_dict, ensure_ascii=False),
                "rejection_reason": reason
            })
        
        df_rejects = pd.DataFrame(reject_records)
        df_rejects.to_sql("rejects", con=self.conn, if_exists="append", index=False)
        rejected_count = len(df_rejects)
        logger.warning(f"Logged {rejected_count} rejected rows from '{source_table}' | Reason: {reason}")
        return rejected_count

    def load_csv_staging(self, csv_data: Dict[str, pd.DataFrame]) -> Tuple[int, int]:
        """Maps discovered CSV DataFrames to staging tables, applies validation, and logs rejects."""
        total_loaded = 0
        total_rejected = 0

        mapping = {
            "olist_orders_dataset.csv": ("staging_orders", "order_id"),
            "olist_order_items_dataset.csv": ("staging_order_items", "order_id"),
            "olist_products_dataset.csv": ("staging_products", "product_id"),
            "olist_order_reviews_dataset.csv": ("staging_reviews", "review_id"),
            "olist_customers_dataset.csv": ("staging_customers", "customer_id"),
            "product_category_name_translation.csv": ("staging_category_translation", "product_category_name")
        }

        for file_name, df in csv_data.items():
            if file_name not in mapping:
                logger.info(f"Skipping CSV without staging mapping: {file_name}")
                continue

            target_table, primary_key = mapping[file_name]

            # Validation: Check for null primary key
            null_pk_mask = df[primary_key].isna()
            rejected_df = df[null_pk_mask]
            clean_df = df[~null_pk_mask]

            if not rejected_df.empty:
                rejected_cnt = self.log_rejects(target_table, rejected_df, f"Missing primary key column '{primary_key}'")
                total_rejected += rejected_cnt

            # Load clean rows into staging
            clean_df.to_sql(target_table, con=self.conn, if_exists="replace", index=False)
            loaded_cnt = len(clean_df)
            total_loaded += loaded_cnt
            logger.info(f"Loaded {loaded_cnt:,} valid rows into '{target_table}' from '{file_name}'")

        return total_loaded, total_rejected

    def load_api_staging(self, df_api: pd.DataFrame) -> Tuple[int, int]:
        """Validates live API DataFrame and loads into staging_api_products."""
        if df_api.empty:
            return 0, 0

        # Validate API products
        null_id_mask = df_api["id"].isna() | (df_api["price"] < 0)
        rejected_df = df_api[null_id_mask]
        clean_df = df_api[~null_id_mask].copy()

        total_rejected = 0
        if not rejected_df.empty:
            total_rejected = self.log_rejects("staging_api_products", rejected_df, "Invalid API product id or negative price")

        # Convert complex columns (e.g. lists, dicts like tags, dimensions) to JSON string if present
        for col in clean_df.columns:
            if clean_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                clean_df[col] = clean_df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x))

        clean_df.to_sql("staging_api_products", con=self.conn, if_exists="replace", index=False)
        loaded_cnt = len(clean_df)
        logger.info(f"Loaded {loaded_cnt} valid live API products into 'staging_api_products'")
        return loaded_cnt, total_rejected

    def close(self):
        self.conn.close()
