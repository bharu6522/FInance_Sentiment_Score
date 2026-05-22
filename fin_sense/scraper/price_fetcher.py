import yfinance as yf 
import sqlite3
import os 
import pandas as pd
from datetime import timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH","data/finsense.db")

ASSETS = {
    "^NSEI":   "NIFTY",    # Nifty 50
    "GC=F":    "GOLD",     # Gold futures
    "BTC-USD": "CRYPTO",   # Bitcoin
}

def fetch_prices() -> list[dict]:
    records = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days= 365)

    for ticker, label in ASSETS.items():
            try:
                df = yf.download(ticker,
                                   start= start_date.strftime("%Y-%m-%d"),
                                   end = end_date.strftime("%Y-%m-%d"),
                                   progress = False,
                                   auto_adjust = True
                  )
                
                if df.empty:
                        print(f"[prices] No data for ticker: {ticker}")
                        continue
                  
                df = df.reset_index()
                df = df.sort_values("Date")

                df["return_1d"] = df["Close"].pct_change()

                for idx, row in df.iterrows():
                      try:
                          open_val = float(row["Open"].iloc[0]) if hasattr(row["Open"], 'iloc') else float(row["Open"])
                          high_val = float(row["High"].iloc[0]) if hasattr(row["High"], 'iloc') else float(row["High"])
                          low_val = float(row["Low"].iloc[0]) if hasattr(row["Low"], 'iloc') else float(row["Low"])
                          close_val = float(row["Close"].iloc[0]) if hasattr(row["Close"], 'iloc') else float(row["Close"])
                          volume_val = float(row["Volume"].iloc[0]) if hasattr(row["Volume"], 'iloc') else float(row["Volume"])
                          return_val = float(row["return_1d"].iloc[0]) if hasattr(row["return_1d"], 'iloc') else float(row["return_1d"])
                          
                          records.append({"asset":label,
                                        "date" : str(row["Date"])[:10],
                                        "open":      round(open_val,  2),
                                        "high":      round(high_val,  2),
                                        "low":       round(low_val,   2),
                                        "close":     round(close_val, 2),
                                        "volume":    volume_val if pd.notna(volume_val) and volume_val > 0 else 0.0,
                                        "return_1d": round(return_val, 5) if pd.notna(return_val) else 0.0,
                                      })
                      except (ValueError, TypeError, AttributeError) as e:
                          print(f"[prices] Skipped row for {label}: {e}")
                          continue
                          
                print(f"[prices] Fetched {len(df)} rows for {label}")

            except Exception as e:
                  print(f"[prices] Failed for {ticker}: {e}")

    return records

def save_prices(records : list[dict]) -> int :
      
      conn = sqlite3.connect(DB_PATH)
      cursor = conn.cursor()
      saved = 0

      for record in records:
            try:
                  cursor.execute(
""" INSERT OR IGNORE INTO prices(asset, date, open, high, low, close, volume, return_1d) 
                                 VALUES(:asset, :date, :open, :high, :low, :close, :volume, :return_1d)
""",record)
                  
                  if cursor.rowcount == 1:
                        saved +=1 
                        
                  
            except Exception as e:
                  print(f"failed to save the rows: {e}")
        
      conn.commit()
      conn.close()
      print(f"[prices] Saved {saved} new price rows")
      return saved


def run_price_fetcher():
    records = fetch_prices()
    saved   = save_prices(records)
    return saved


if __name__ == "__main__":
    run_price_fetcher()
      


                  
                  
