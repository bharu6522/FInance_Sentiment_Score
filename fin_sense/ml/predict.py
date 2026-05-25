import sqlite3
import os 
from dotenv import load_dotenv
import pickle
import pandas as pd
import numpy as np 
from datetime import datetime, timedelta

load_dotenv()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finsense.db"))
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "model.pkl"))

FEATURES = [
     "return_1d",
    "return_2d",
    "return_3d",
    "volatility_5d",
    "avg_return_5d",

    "volume_change",
    "avg_sentiment",
    "max_sentiment",
    "min_sentiment",

    "sentiment_momentum",
    "positive_count",
    "negative_count",
    "high_impact_count",
    "article_count"
]


def load_model():
    with open(MODEL_PATH,"rb") as f:
        return pickle.load(f)
    

def get_latest_feature(asset: str)-> pd.DataFrame | None:

    conn = sqlite3.connect(DB_PATH)

    prices = pd.read_sql_query("""
    SELECT date, close, return_1d, volume FROM prices 
                               where asset = ? 
                               ORDER BY date DESC LIMIT 10 """, conn, params= (asset,))
    
    since = (datetime.now()-timedelta(hours =24)).strftime("%Y-%m-%d %H:%M:%S")
    sentiment = pd.read_sql_query("""
    SELECT count(*) as article_count,
            AVG(sentiment_score) as avg_sentiment,
                                  MIN(sentiment_score) as min_sentiment,
                                  MAX(sentiment_score) as max_sentiment,
                                  SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
                                  SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
                                  SUM(CASE WHEN impact='high' THEN 1 ELSE 0 END) AS high_impact_count
                                  FROM articles
                                  WHERE asset_tag = ?
                                  AND published_at >= ?
                                  AND is_processed = 1 """, conn, params=(asset.lower(),since))
    

    conn.close()

    if prices.empty or len(prices) < 5:
        print(f"[predict] Not enough price data for {asset}")
        return None
    
    prices = prices.sort_values("date")

    row = {
        "return_1d":         prices["return_1d"].iloc[-1],
        "return_2d":         prices["return_1d"].iloc[-2],
        "return_3d":         prices["return_1d"].iloc[-3],
        "volatility_5d":     prices["return_1d"].tail(5).std(),
        "avg_return_5d":     prices["return_1d"].tail(5).mean(),
        "volume_change":     prices["volume"].pct_change().iloc[-1],
        "avg_sentiment":     sentiment["avg_sentiment"].iloc[0] or 0.0,
        "max_sentiment":     sentiment["max_sentiment"].iloc[0] or 0.0,
        "min_sentiment":     sentiment["min_sentiment"].iloc[0] or 0.0,
        "sentiment_momentum":0.0,
        "positive_count":    sentiment["positive_count"].iloc[0] or 0,
        "negative_count":    sentiment["negative_count"].iloc[0] or 0,
        "high_impact_count": sentiment["high_impact_count"].iloc[0] or 0,
        "article_count":     sentiment["article_count"].iloc[0] or 0,
    }

    return pd.DataFrame([row])


def prdict_asset(asset:str)-> dict|None:
    bundle = load_model()
    model = bundle["model"]
    encoder = bundle["encoder"]
    
    X = get_latest_feature(asset)
    if X is None:
        return None
    
    X= X[FEATURES].replace([np.inf, -np.inf],np.nan).fillna(0)

    proba = model.predict_proba(X)[0] # list of prob for all classes 
    pred_index = np.argmax(proba) # index of max probability 
    pred_label = encoder.inverse_transform([pred_index])[0]
    confidence = round(proba[pred_index],3)

    result = {
        "asset":      asset,
        "prediction": pred_label,
        "confidence": confidence,
        "proba":      dict(zip(encoder.classes_, proba.round(3))),
        "date":       datetime.now().strftime("%Y-%m-%d")
        }

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    INSERT OR REPLACE INTO predictions 
                 (asset, prediction_date, predicted_label, confidence)
                 VALUES(?, ?, ?, ?) """, (asset, result["date"], pred_label, confidence))
    
    conn.commit()
    conn.close()

    return result

if __name__ == "__main__":

    for asset in ['NIFTY',"GOLD","CRYPTO"]:
        result = prdict_asset(asset)

        if result:
            print(f"\nAsset      : {result['asset']}")
            print(f"Prediction : {result['prediction']}")
            print(f"Confidence : {result['confidence']}")
            print(f"Breakdown  : {result['proba']}")
    