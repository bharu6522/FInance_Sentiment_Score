import yfinance as yf 
import sqlite3
import os 
import pandas as pd
from datetime import timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finsense.db"))

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
                
                # Ensure simple column index (not MultiIndex)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # Make column names lowercase
                df.columns = df.columns.str.lower()
                
                # Get the date from index
                df['date'] = df.index.astype(str)
                
                # Calculate returns
                df['return_1d'] = df['close'].pct_change()
                
                print(f"[prices] Fetched {len(df)} rows for {ticker}")

                # Process each row
                for idx, row in df.iterrows():
                      try:
                          close_val = float(row['close'])
                          
                          # Skip if no valid close price
                          if close_val <= 0:
                              continue
                          
                          date_str = str(row['date'])[:10]
                          
                          row_record = {
                              "asset": label,
                              "date": date_str,
                              "open": round(float(row['open']), 2),
                              "high": round(float(row['high']), 2),
                              "low": round(float(row['low']), 2),
                              "close": round(close_val, 2),
                              "volume": round(float(row['volume']), 2),
                              "return_1d": round(float(row['return_1d']) if pd.notna(row['return_1d']) else 0.0, 5),
                          }
                          records.append(row_record)
                          
                      except Exception as e:
                          print(f"[prices] Error processing row {idx} for {label}: {e}")
                          continue
                          
                print(f"[prices] Fetched {len(df)} rows for {label}, appended {len([r for r in records if r['asset'] == label])} to records")

            except Exception as e:
                  print(f"[prices] Failed for {ticker}: {e}")

    return records

def save_prices(records : list[dict]) -> int :
      
      conn = sqlite3.connect(DB_PATH)
      cursor = conn.cursor()
      
      print(f"[prices] Attempting to save {len(records)} records")
      
      if not records:
            print("[prices] No records to save")
            conn.close()
            return 0

      try:
            # Use executemany for better performance
            values = [(r["asset"], r["date"], r["open"], r["high"], r["low"], r["close"], r["volume"], r["return_1d"]) 
                      for r in records]
            
            cursor.executemany("""
INSERT OR IGNORE INTO prices(asset, date, open, high, low, close, volume, return_1d) 
VALUES(?, ?, ?, ?, ?, ?, ?, ?)
""", values)
            
            conn.commit()
            saved = cursor.rowcount
            print(f"[prices] Successfully saved {saved} new price rows")
            
      except Exception as e:
            print(f"[prices] Error saving records: {e}")
            saved = 0
            
      conn.close()
      return saved


def run_price_fetcher():
    records = fetch_prices()
    saved   = save_prices(records)
    return saved


if __name__ == "__main__":
    run_price_fetcher()
      


                  
                  
