import os 
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware 

import sqlite3
import pandas as pd 


from fin_sense.ml.predict import predict_asset
from fin_sense.scraper.news_scraper import run_news_scraper
from fin_sense.scraper.price_fetcher import run_price_fetcher
from fin_sense.sentiment.batch_processor import run_batch_processor

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/finsense.db")

app = FastAPI(title="FinSense API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "FinSense API is running"}


@app.get("/predictions")
def get_predictions():
    conn = sqlite3.connect(DB_PATH)
    rows = pd.read_sql_query("""
    SELECT asset, prediction_date, predicted_label, confidence
        FROM predictions
        ORDER BY prediction_date DESC
        LIMIT 9 """,conn)
    
    conn.close()
    return rows.to_dict(orient= 'records')


@app.get("/news")
def get_news(asset: str = None, limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT headline, source, asset_tag, sentiment_label,
        sentiment_score, impact, explanation, published_at
        FROM articles
        WHERE is_processed = 1
    """

    params = []
    if asset:
        query += "AND asset_tag = ?"
        params.append(asset.lower())

    rows = pd.read_sql_query(query, conn,params = params)
    conn.close()
    return rows.to_dict(orient= "records")


@app.get("/sentiment/trend")
def sentiment_trend(asset: str= "nifty", days:int = 7 ):
    conn = sqlite3.connect(DB_PATH)
    query = """ SELECT
            DATE(published_at)   AS date,
            AVG(sentiment_score) AS avg_sentiment,
            COUNT(*)             AS article_count
        FROM articles
        WHERE asset_tag    = ?
          AND is_processed = 1
          AND published_at >= DATE('now', ? || ' days')
        GROUP BY DATE(published_at)
        ORDER BY date ASC """
    rows = pd.read_sql_query(query, conn,params=(asset.lower(),f"-{days}"))
    conn.close()

    return rows.to_dict(orient= "records")


@app.post("/pipeline/trigger")
def run_pipeline():
    try:
        run_news_scraper()
        run_price_fetcher()
        run_batch_processor()
        for asset in ["NIFTY","GOLD","CRYPTO"]:
            predict_asset(asset)
        return {"status": "pipeline completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.get("/predict/{asset}")
def predict(asset: str):
    result = predict_asset(asset.upper())
    if not result:
        raise HTTPException(status_code=404,
                            detail=f"Could not predict for {asset}")
    
    return result

@app.get("/stats")
def stats():
    conn = sqlite3.connect(DB_PATH)
    return {
        "total_articles":  conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "scored_articles": conn.execute("SELECT COUNT(*) FROM articles WHERE is_processed=1").fetchone()[0],
        "total_prices":    conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0],
        "predictions":     conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],
    }

    
