import os
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
from src.config import RAW_DATA_DIR, logger

class CSVExtractor:
    """Scans and extracts arbitrary raw CSV files from /data/raw/ dynamically."""

    def __init__(self, raw_dir: Path = RAW_DATA_DIR):
        self.raw_dir = Path(raw_dir)

    def discover_files(self) -> list:
        """Finds all CSV files in the raw data directory."""
        if not self.raw_dir.exists():
            logger.warning(f"Raw data directory {self.raw_dir} does not exist.")
            return []
        
        csv_files = list(self.raw_dir.glob("*.csv"))
        logger.info(f"Discovered {len(csv_files)} CSV files in {self.raw_dir}")
        for file in csv_files:
            file_size_mb = round(file.stat().st_size / (1024 * 1024), 2)
            logger.info(f" -> Found: {file.name} ({file_size_mb} MB)")
        return csv_files

    def extract_all(self) -> Tuple[Dict[str, pd.DataFrame], int]:
        """Reads all discovered CSVs into pandas DataFrames without hardcoding filenames."""
        csv_files = self.discover_files()
        extracted_data = {}
        total_rows_extracted = 0

        for file_path in csv_files:
            try:
                # Read CSV dynamically
                df = pd.read_csv(file_path, low_memory=False)
                row_count = len(df)
                total_rows_extracted += row_count
                extracted_data[file_path.name] = df
                logger.info(f"Extracted {row_count:,} rows from '{file_path.name}' with columns: {list(df.columns)}")
            except Exception as e:
                logger.error(f"Failed to read raw CSV file '{file_path.name}': {str(e)}")

        return extracted_data, total_rows_extracted

if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()
    extractor = CSVExtractor()
    data, count = extractor.extract_all()
    print(f"Total CSV rows extracted: {count:,}")
