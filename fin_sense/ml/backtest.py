import sqlite3
import os 
import pandas as pd 
import numpy as np 
import pickle 
from dotenv import load_dotenv
from ml.feature_builder import build_feature_matrix

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

def backtest(days: int = 30):
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)

    model = bundle["model"]
    encoder = bundle["encoder"]

    df = pd.read_csv(r"data\\backtest_holdout.csv")
    df = df.replace([np.inf, -np.inf],np.nan).dropna(subset= FEATURES)

    df = df.sort_values("date")
    test = df.tail(days*3)

    if test.empty:
        print("[Backtest] no enough data")
        return 
    
    X= test[FEATURES]
    y_true = encoder.transform(test["target"])

    y_pred = model.predict(X)

    test = test.copy()
    
        # Prediction:
        # new data  →  model.predict()  →  1  →  encoder.inverse_transform()  →  "FLAT"

    test["predicted"] = encoder.inverse_transform(y_pred)
    test["correct"] = test["predicted"] == test["target"]

    print(f"\n[backtest] Last {days} days — per asset accuracy:")
    for asset in test["asset"].unique():
        subset   = test[test["asset"] == asset]
        accuracy = subset["correct"].mean()
        print(f"  {asset:<10} {len(subset)} days   accuracy: {accuracy:.1%}")

    print(f"\n[backtest] Overall accuracy: {test['correct'].mean():.1%}")

    print("\n[backtest] Sample predictions vs actual:")
    print(test[["asset", "date", "target", "predicted", "correct"]]
          .tail(15)
          .to_string(index=False))


if __name__ == "__main__":
    backtest(days= 30)

