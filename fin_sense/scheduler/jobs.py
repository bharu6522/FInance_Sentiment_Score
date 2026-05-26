import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from scraper.news_scraper import run_news_scraper
from scraper.price_fetcher import run_price_fetcher
from sentiment.batch_processor import run_batch_processor
from ml.predict import predict_asset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("=== Pipeline started ===")
    try:
        run_news_scraper()
        run_price_fetcher()
        run_batch_processor()
        for asset in ["NIFTY", "GOLD", "CRYPTO"]:
            predict_asset(asset)
        logger.info("=== Pipeline complete ===")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
