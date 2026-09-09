import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import DATABASE_URI, DB_PATH, SQL_DIR, logger

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URI, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db_connection():
    """Returns a direct sqlite3 connection for optimized batch pandas operations."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes tables and views by executing DDL scripts in /sql directory."""
    logger.info(f"Initializing database at: {DB_PATH}")
    sql_files = [
        "01_staging_tables.sql",
        "02_star_schema.sql",
        "03_transformations.sql",
        "04_seo_opportunity_report.sql",
        "05_decision_kpis.sql"
    ]
    
    with engine.begin() as conn:
        for sql_file in sql_files:
            file_path = SQL_DIR / sql_file
            if file_path.exists():
                logger.info(f"Executing SQL script: {sql_file}")
                sql_content = file_path.read_text(encoding="utf-8")
                # Split commands by semicolon for execution if needed or execute raw batch
                statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
                for statement in statements:
                    conn.execute(text(statement))
            else:
                logger.warning(f"SQL file not found: {file_path}")

def execute_sql_file(sql_file_name: str):
    """Executes a specific SQL file from /sql directory."""
    file_path = SQL_DIR / sql_file_name
    if not file_path.exists():
        raise FileNotFoundError(f"SQL script {sql_file_name} does not exist at {file_path}")
    
    logger.info(f"Running transformation script: {sql_file_name}")
    sql_content = file_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
        for statement in statements:
            conn.execute(text(statement))
