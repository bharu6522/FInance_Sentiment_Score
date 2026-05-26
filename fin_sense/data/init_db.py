import sqlite3
import os 

# Correct path: this file is in fin_sense/data/, so go up one level and into data/
# DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fin_sense", "data", "finsense.db")
# Or simpler: just use the file's directory
# DB_PATH = os.path.join(os.path.dirname(__file__), "finsense.db")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "finsense.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor= conn.cursor()

cursor.executescript("""

CREATE TABLE IF NOT EXISTS articles(
        
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    source TEXT,
    url TEXT UNIQUE,
    published_at    TEXT,
    asset_tag       TEXT,          
    sentiment_label TEXT,          
    sentiment_score REAL,          -- -1.0 to +1.0
    impact          TEXT,          
    explanation     TEXT,          
    is_processed    INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
                     );

CREATE TABLE IF NOT EXISTS prices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asset       TEXT NOT NULL,     -- NIFTY / GOLD / BTC-USD
    date        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    return_1d   REAL,              -- (close - prev_close) / prev_close
    UNIQUE(asset, date)
);
                     
CREATE TABLE IF NOT EXISTS predictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    asset               TEXT NOT NULL,
    prediction_date     TEXT NOT NULL,
    predicted_label     TEXT,      -- UP / DOWN / FLAT
    confidence          REAL,
    avg_sentiment_24h   REAL,
    top_shap_driver     TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(asset, prediction_date)
);
                     
CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(is_processed);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_prices_asset_date  ON prices(asset, date);
                     

""")

conn.commit()
conn.close()
print("data base initialized successfully")

