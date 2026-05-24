import sqlite3
import pandas as pd 
import os 
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finsense.db"))

def get_sentiment_features(conn: sqlite3.Connection)->pd.DataFrame:

    df = pd.read_sql_query(""" SELECT 
            asset_tag AS asset, 
            DATE(published_at) AS date,
            COUNT(*)                            AS article_count,
            AVG(sentiment_score)                AS avg_sentiment,
            MAX(sentiment_score)                AS max_sentiment,
            MIN(sentiment_score)                AS min_sentiment,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
            SUM(CASE WHEN sentiment_label = 'neutral'  THEN 1 ELSE 0 END) AS neutral_count,
            SUM(CASE WHEN impact = 'high'              THEN 1 ELSE 0 END) AS high_impact_count
        FROM articles
        WHERE is_processed = 1
          AND asset_tag != 'general'
        GROUP BY asset_tag, DATE(published_at)
        ORDER BY date ASC
     """, conn)
    
    return df 



def get_price_features(conn: sqlite3.Connection) -> pd.DataFrame:

    df = pd.read_sql_query(""" SELECT asset,date,close,return_1d,volume FROM prices ORDER BY asset, date ASC 
                           """, conn  )
    
    result = []

    for asset in df['asset'].unique():
        asset_df = df[df['asset'] == asset].copy()
        asset_df['return_2d'] = asset_df['return_1d'].shift(1)
        asset_df['return_3d'] = asset_df['return_1d'].shift(2)
        asset_df["volatility_5d"]   = asset_df["return_1d"].rolling(5).std()
        asset_df["avg_return_5d"]   = asset_df["return_1d"].rolling(5).mean()
        asset_df["volume_change"]   = asset_df["volume"].pct_change()

        
        asset_df["next_return"]  = asset_df["return_1d"].shift(-1)
        asset_df["target"] = asset_df["next_return"].apply(
            lambda x: "UP" if x > 0.005 else ("DOWN" if x < -0.005 else "FLAT")
        )

        result.append(asset_df)

    return pd.concat(result, ignore_index= True)




def build_feature_matrix() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)

    sentiment_df= get_sentiment_features(conn)
    prices_df = get_price_features(conn)


    # normalize asset names to match between tables
    # articles use: nifty, gold, crypto
    # prices use  : NIFTY, GOLD, CRYPTO
    sentiment_df["asset"] = sentiment_df["asset"].str.upper()

    df = pd.merge(
        prices_df,
        sentiment_df,
        on=["asset", "date"],
        how="left"
    )

    sentiment_cols = [
        "article_count", "avg_sentiment", "max_sentiment",
        "min_sentiment", "positive_count", "negative_count",
        "neutral_count", "high_impact_count"
    ]

    df[sentiment_cols] = df[sentiment_cols].fillna(0)
    # add sentiment momentum (today vs yesterday avg sentiment)
    df["sentiment_momentum"] = df.groupby("asset")["avg_sentiment"].diff()

    df = df.dropna(subset=['target'])
    df =df.dropna(subset= ["return_2d", "return_3d", "volatility_5d"])

    print(f"[features] Built {len(df)} feature rows")
    print(f"[features] Assets: {df['asset'].unique()}")
    print(f"[features] Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"[features] Target distribution:\n{df['target'].value_counts()}")

    return df



if __name__ == "__main__":
    df = build_feature_matrix()
    print("\n--- Sample feature row ---")
    print(df[df["asset"] == "NIFTY"].tail(3)[[
        "asset", "date", "avg_sentiment", "sentiment_momentum",
        "high_impact_count", "return_1d", "volatility_5d", "target"
    ]].to_string())


    
