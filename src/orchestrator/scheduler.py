import time
from datetime import datetime
import pandas as pd
from sqlalchemy import text
import schedule
from src.config import logger, setup_logging
from src.db import init_db, engine, get_db_connection
from src.extract.csv_extractor import CSVExtractor
from src.extract.api_extractor import APIExtractor
from src.load.staging_loader import StagingLoader
from src.load.star_schema_loader import StarSchemaLoader
from src.transform.sql_transformer import SQLTransformer

class PipelineOrchestrator:
    """Orchestrates end-to-end extraction, validation, loading, star schema building, and monitoring."""

    def __init__(self):
        setup_logging()

    def run_full_pipeline(self) -> dict:
        """Executes full ETL pipeline: CSV + API extract, staging, star schema, SQL views, logging to monitoring."""
        start_time = datetime.now()
        logger.info("==================================================")
        logger.info(f"STARTING E-COMMERCE DATA PIPELINE RUN at {start_time}")
        logger.info("==================================================")

        run_status = "SUCCESS"
        error_msg = None
        extracted_rows = 0
        loaded_rows = 0
        rejected_rows = 0

        try:
            # 0. Initialize DB schemas & tables
            init_db()

            # 1. Extract Layer
            csv_extractor = CSVExtractor()
            csv_data, csv_count = csv_extractor.extract_all()

            api_extractor = APIExtractor()
            df_api, api_count = api_extractor.fetch_products()

            extracted_rows = csv_count + api_count

            # 2. Validate & Load to Staging Layer
            staging_loader = StagingLoader()
            c_loaded, c_rejected = staging_loader.load_csv_staging(csv_data)
            a_loaded, a_rejected = staging_loader.load_api_staging(df_api)
            staging_loader.close()

            rejected_rows = c_rejected + a_rejected

            # 3. Load Star Schema Dimensions & Fact Table
            star_loader = StarSchemaLoader()
            loaded_rows = star_loader.run_all()
            star_loader.close()

            # 4. SQL Transformations & View Refresh
            transformer = SQLTransformer()
            transformer.create_views()
            
            # Print quick SEO report preview in logs
            df_seo = transformer.get_seo_opportunity_report(limit=5)
            logger.info("\n--- SEO OPPORTUNITY REPORT PREVIEW (TOP 5) ---")
            logger.info(f"\n{df_seo.to_string(index=False)}")
            transformer.close()

        except Exception as e:
            run_status = "FAILED"
            error_msg = str(e)
            logger.error(f"Pipeline execution failed: {error_msg}", exc_info=True)

        end_time = datetime.now()
        duration_sec = round((end_time - start_time).total_seconds(), 2)

        logger.info("--------------------------------------------------")
        logger.info(f"PIPELINE COMPLETED in {duration_sec}s | Status: {run_status}")
        logger.info(f"Extracted: {extracted_rows:,} | Loaded Facts: {loaded_rows:,} | Rejects: {rejected_rows:,}")
        logger.info("--------------------------------------------------")

        # 5. Log run metrics to monitoring table
        self.log_monitoring_metrics(
            pipeline_name="FULL_ECOMMERCE_ETL",
            status=run_status,
            start_time=start_time,
            end_time=end_time,
            duration=duration_sec,
            extracted=extracted_rows,
            loaded=loaded_rows,
            rejected=rejected_rows,
            error=error_msg
        )

        return {
            "status": run_status,
            "duration_seconds": duration_sec,
            "extracted_rows": extracted_rows,
            "loaded_rows": loaded_rows,
            "rejected_rows": rejected_rows
        }

    def log_monitoring_metrics(self, pipeline_name: str, status: str, start_time: datetime,
                               end_time: datetime, duration: float, extracted: int,
                               loaded: int, rejected: int, error: str):
        """Records execution stats into pipeline_monitoring table."""
        sql = """
        INSERT INTO pipeline_monitoring (
            pipeline_name, status, start_time, end_time, duration_seconds,
            extracted_rows, loaded_rows, rejected_rows, error_message
        ) VALUES (
            :name, :status, :start, :end, :duration, :extracted, :loaded, :rejected, :error
        )
        """
        with engine.begin() as conn:
            conn.execute(text(sql), {
                "name": pipeline_name,
                "status": status,
                "start": start_time,
                "end": end_time,
                "duration": duration,
                "extracted": extracted,
                "loaded": loaded,
                "rejected": rejected,
                "error": error
            })

    def run_scheduled_daemon(self, interval_minutes: int = 60):
        """Runs the live pipeline periodically."""
        logger.info(f"Starting pipeline scheduler daemon every {interval_minutes} minutes...")
        
        # Run immediately once
        self.run_full_pipeline()

        # Schedule recurring runs
        schedule.every(interval_minutes).minutes.do(self.run_full_pipeline)

        try:
            while True:
                schedule.run_pending()
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Scheduler daemon stopped by user.")
