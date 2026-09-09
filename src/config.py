import os
import logging
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

# Database Configuration
DB_PATH = DATA_DIR / "ecommerce.db"
DATABASE_URI = os.getenv("DATABASE_URI", f"sqlite:///{DB_PATH}")

# Live API Configuration
DUMMYJSON_API_URL = "https://dummyjson.com/products"
API_FETCH_LIMIT = 100
API_MAX_RETRIES = 5
API_BACKOFF_FACTOR = 1.0

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Logging Setup
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(DATA_DIR / "pipeline.log", encoding="utf-8")
        ]
    )

logger = logging.getLogger("EcommercePipeline")
