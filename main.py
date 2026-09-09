import argparse
import sys
from src.config import setup_logging, logger
from src.orchestrator.scheduler import PipelineOrchestrator
from src.transform.sql_transformer import SQLTransformer

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="E-Commerce End-to-End Data Ingestion Pipeline")
    parser.add_argument("--run-once", action="store_true", default=True, help="Run full pipeline once end-to-end")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled daemon mode")
    parser.add_argument("--interval", type=int, default=60, help="Scheduler interval in minutes (default: 60)")
    parser.add_argument("--report", action="store_true", help="Print analytical SQL reports to console")

    args = parser.parse_args()

    orchestrator = PipelineOrchestrator()

    if args.schedule:
        orchestrator.run_scheduled_daemon(interval_minutes=args.interval)
    else:
        results = orchestrator.run_full_pipeline()
        
        if args.report or results["status"] == "SUCCESS":
            print("\n=======================================================")
            print("         SEO OPPORTUNITY REPORT (TOP CATEGORIES)       ")
            print("=======================================================")
            transformer = SQLTransformer()
            df_seo = transformer.get_seo_opportunity_report(limit=10)
            print(df_seo.to_string(index=False))

            print("\n=======================================================")
            print("        ORDER FUNNEL & CONVERSION METRICS SUMMARY       ")
            print("=======================================================")
            df_funnel = transformer.get_order_funnel()
            print(df_funnel.to_string(index=False))
            transformer.close()

if __name__ == "__main__":
    main()
