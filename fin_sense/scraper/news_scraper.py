import requests
from bs4 import BeautifulSoup 
import sqlite3
import os 
from datetime import datetime
from dotenv import load_dotenv 

load_dotenv()
DB_PATH = os.getenv("DB_PATH","data/finsense.db")

HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Keywords to tag which asset an article is about
ASSET_KEYWORDS = {
    "nifty":  ["nifty", "sensex", "bse", "nse", "stock market", "equity"],
    "gold":   ["gold", "silver", "mcx", "bullion"],
    "crypto": ["bitcoin", "crypto", "ethereum", "btc", "web3", "blockchain"],
    "rbi":    ["rbi", "repo rate", "inflation", "monetary policy", "interest rate"],
}

def tag_asset(headline: str) -> str:
    headline_lower = headline.lower()
    for asset, keyword in ASSET_KEYWORDS.items():
        if any(kw in headline_lower for kw in keyword):
            return asset 
    return "general"


def scrape_moneycontrol() -> list[dict]:
    urls= ["https://www.moneycontrol.com/news/business/markets/",
           "https://www.moneycontrol.com/news/business/economy/",
           "https://www.moneycontrol.com/news/business/cryptocurrency/"
           ]
    articles = []
    for url in urls:
        try:

            response = requests.get(url, headers= HEADERS, timeout= 10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # MoneyControl wraps headlines in <li> tags with class 'clearfix'
            items = soup.select("ul.lst_story_small li") or \
            soup.select("li.clearfix") or \
            soup.select(".news_listing li")

            for item in items[:15]:
                anchor = item.find("a")
                if not anchor:
                    continue

                headline = anchor.get_text(strip= True)
                link = anchor.get("href","")

                if not headline or len(headline) < 20:
                    continue

                articles.append({
                    "headline": headline,
                    "source":       "moneycontrol",
                    "url":          link,
                    "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "asset_tag":    tag_asset(headline),
                })


        except Exception as e:
            print(f"[scraper] Failed to fetch {url}: {e}")
    
    return articles


def save_articles(articles: list[dict]) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0

    for article in articles:
        try:
            cursor.execute("""
        INSERT OR IGNORE INTO articles(headline, source, url, published_at, asset_tag)
                           VALUES(:headline, :source, :url, :published_at, :asset_tag)
""", article)

            if cursor.rowcount == 1:
                saved += 1

        except Exception as e:
            print(f"scraper failed to save article: {e}")
    
    conn.commit()
    conn.close()
    return saved


def run_news_scraper():
    articles = scrape_moneycontrol()
    saved = save_articles(articles)
    return saved 

if __name__ == "__main__":
    run_news_scraper()




