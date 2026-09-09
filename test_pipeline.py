r"""
Quick Verification & Testing Script for E-Commerce Data Pipeline
Run: .\.venv\Scripts\python.exe test_pipeline.py
"""

import pandas as pd
from src.orchestrator.scheduler import PipelineOrchestrator
from src.transform.sql_transformer import SQLTransformer
from src.db import get_db_connection

def test_full_pipeline():
    print("=" * 60)
    print("1. RUNNING FULL DATA INGESTION PIPELINE")
    print("=" * 60)
    orchestrator = PipelineOrchestrator()
    result = orchestrator.run_full_pipeline()
    print(f"\nPipeline Run Output: {result}")

    print("\n" + "=" * 60)
    print("2. FETCHING SEO OPPORTUNITY REPORT (TOP 10)")
    print("=" * 60)
    transformer = SQLTransformer()
    df_seo = transformer.get_seo_opportunity_report(limit=10)
    print(df_seo.to_string(index=False))

    print("\n" + "=" * 60)
    print("3. FETCHING ORDER FUNNEL & CONVERSION METRICS")
    print("=" * 60)
    df_funnel = transformer.get_order_funnel()
    print(df_funnel.to_string(index=False))

    print("\n" + "=" * 60)
    print("4. FETCHING REVIEW SENTIMENT VS ORDER VOLUME (TOP 5)")
    print("=" * 60)
    df_sentiment = transformer.get_sentiment_vs_volume(limit=5)
    print(df_sentiment.to_string(index=False))

    print("\n" + "=" * 60)
    print("5. CHECKING PIPELINE MONITORING AUDIT LOGS")
    print("=" * 60)
    conn = get_db_connection()
    df_logs = pd.read_sql_query("SELECT id, pipeline_name, status, duration_seconds, extracted_rows, loaded_rows, rejected_rows FROM pipeline_monitoring ORDER BY id DESC LIMIT 5", conn)
    print(df_logs.to_string(index=False))

    transformer.close()
    conn.close()
    print("\n[SUCCESS] TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_pipeline()
