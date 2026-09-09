import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import pandas as pd
from typing import Tuple, List, Dict
from src.config import DUMMYJSON_API_URL, API_FETCH_LIMIT, API_MAX_RETRIES, API_BACKOFF_FACTOR, logger

class APIExtractor:
    """Extracts live product catalog data from DummyJSON API with exponential backoff & retry logic."""

    def __init__(self, base_url: str = DUMMYJSON_API_URL):
        self.base_url = base_url
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Creates a requests session configured with exponential backoff retries for 429 & 5xx errors."""
        session = requests.Session()
        retry_strategy = Retry(
            total=API_MAX_RETRIES,
            backoff_factor=API_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_products(self) -> Tuple[pd.DataFrame, int]:
        """Paginates through DummyJSON API and extracts all products."""
        logger.info(f"Starting live API pull from {self.base_url}")
        all_products: List[Dict] = []
        skip = 0
        limit = API_FETCH_LIMIT
        total = None

        while total is None or skip < total:
            url = f"{self.base_url}?limit={limit}&skip={skip}"
            try:
                logger.info(f"Fetching API page: skip={skip}, limit={limit}")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                products = data.get("products", [])
                total = data.get("total", len(products))
                all_products.extend(products)
                
                logger.info(f"Retrieved {len(products)} products (Cumulative: {len(all_products)}/{total})")
                skip += limit

                # Respectful rate limit delay
                time.sleep(0.2)

            except requests.exceptions.RequestException as e:
                logger.error(f"API extraction error at skip={skip}: {str(e)}")
                break

        df_api = pd.DataFrame(all_products)
        extracted_count = len(df_api)
        logger.info(f"Successfully extracted {extracted_count} total products from live API.")
        return df_api, extracted_count

if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()
    extractor = APIExtractor()
    df, count = extractor.fetch_products()
    print(f"API Products Extracted: {count}")
    print(df.head(2))
