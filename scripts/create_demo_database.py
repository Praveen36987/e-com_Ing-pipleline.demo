"""Build a GitHub-safe analytics snapshot from the local pipeline database.

The snapshot retains every row used by the dashboard's analytical views. It
excludes raw/staging tables and customer details, keeping the portfolio database
small without changing category-level KPIs.
"""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATABASE = PROJECT_ROOT / "data" / "ecommerce.db"
DEMO_DATABASE = PROJECT_ROOT / "data" / "demo_ecommerce.db"
TABLES_TO_COPY = (
    "dim_category",
    "dim_products",
    "dim_time",
    "fact_orders",
    "pipeline_monitoring",
    "rejects",
)
VIEW_SCRIPTS = (
    PROJECT_ROOT / "sql" / "03_transformations.sql",
    PROJECT_ROOT / "sql" / "04_seo_opportunity_report.sql",
    PROJECT_ROOT / "sql" / "05_decision_kpis.sql",
)


def create_table(destination: sqlite3.Connection, source: sqlite3.Connection, table_name: str) -> None:
    schema = source.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)
    ).fetchone()
    if not schema or not schema[0]:
        raise RuntimeError(f"Could not find schema for {table_name}")
    destination.execute(schema[0])


def main() -> None:
    if not SOURCE_DATABASE.exists():
        raise FileNotFoundError(f"Source database not found: {SOURCE_DATABASE}")
    if DEMO_DATABASE.exists():
        raise FileExistsError(
            f"{DEMO_DATABASE} already exists. Delete it explicitly before rebuilding the snapshot."
        )

    with sqlite3.connect(SOURCE_DATABASE) as source, sqlite3.connect(DEMO_DATABASE) as destination:
        destination.execute("ATTACH DATABASE ? AS pipeline_source", (str(SOURCE_DATABASE),))
        for table in TABLES_TO_COPY:
            create_table(destination, source, table)
            destination.execute(f'INSERT INTO "{table}" SELECT * FROM pipeline_source."{table}"')

        destination.executescript(
            """
            CREATE INDEX idx_demo_fact_time ON fact_orders(time_id);
            CREATE INDEX idx_demo_fact_product ON fact_orders(product_id);
            CREATE INDEX idx_demo_fact_category ON fact_orders(category_name);
            """
        )
        destination.commit()
        destination.execute("DETACH DATABASE pipeline_source")
        for sql_file in VIEW_SCRIPTS:
            destination.executescript(sql_file.read_text(encoding="utf-8"))
        destination.commit()
        destination.execute("VACUUM")

    with sqlite3.connect(SOURCE_DATABASE) as source, sqlite3.connect(DEMO_DATABASE) as demo:
        checks = {
            "fact_orders": "SELECT COUNT(*) FROM fact_orders",
            "dim_products": "SELECT COUNT(*) FROM dim_products",
            "dim_time": "SELECT COUNT(*) FROM dim_time",
            "decision_categories": "SELECT COUNT(*) FROM decision_category_scorecard",
            "total_revenue": "SELECT ROUND(SUM(total_amount), 2) FROM fact_orders",
        }
        for label, query in checks.items():
            source_value = source.execute(query).fetchone()[0]
            demo_value = demo.execute(query).fetchone()[0]
            if source_value != demo_value:
                raise RuntimeError(f"Verification failed for {label}: {source_value} != {demo_value}")
            print(f"Verified {label}: {demo_value}")

    size_mb = DEMO_DATABASE.stat().st_size / (1024 * 1024)
    print(f"Created {DEMO_DATABASE} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
