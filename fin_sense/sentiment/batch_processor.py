import sqlite3
import os 
from dotenv import load_dotenv
import time
import logging
from sentiment.finebert_scorer import score_headline
from sentiment.groq_explainer import explain_headline


load_dotenv()

# DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finsense.db"))
DB_PATH= os.getenv("DB_PATH","data/finsense.db")

logging.basicConfig(level= logging.INFO)
logger = logging.getLogger(__name__)

def get_unprocessed_articles(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
select id, headline FROM articles WHERE is_processed = 0 ORDER BY created_at ASC""").fetchall()
    
    return [{"id":r[0],"headline":r[1]} for r in rows]


def update_article(conn: sqlite3.Connection, article_id: int, result: dict):

    conn.execute("""
            UPDATE articles SET
            sentiment_label = ?,
            sentiment_score = ?,
            asset_tag       = ?,
            impact          = ?,
            explanation     = ?,
            is_processed    = 1
             WHERE id = ? 
                 """ , (
        result["sentiment_label"],
        result["sentiment_score"],
        result["asset_tag"],
        result["impact"],
        result.get("explanation"),
        article_id,
    )
    )

    conn.commit()


def mark_failed(conn: sqlite3.Connection, article_id: int):
    conn.execute("""
UPDATE articles SET is_processed = 1,
                 sentiment_label = 'neutral',
                 sentiment_score = 0.0,
                 impact= 'low'
                 WHERE id = ? 
""", (article_id,))
    
    conn.commit()



def run_batch_processor():

    conn = sqlite3.connect(DB_PATH)
    articles = get_unprocessed_articles(conn)

    if not articles:
        logger.info("[batch] No processed article found")
        conn.close()
        return 
    
    logger.info(f"[batch] Found {len(articles)} unprocessed articles")

    success = 0
    failed = 0

    for i,article in enumerate(articles):
        article_id = article["id"]
        headline = article["headline"]
        logger.info(f"[batch] {i+1}/{len(articles)} → {headline[:60]}...")

        result = score_headline(headline)
        if result:
            explanation = explain_headline(
                    headline, 
                    result["sentiment_label"], 
                    result["asset_tag"]
    )
            result["explanation"] = explanation
            update_article(conn, article_id, result)
            success += 1
        else:
            mark_failed(conn, article_id)
            failed += 1

        time.sleep(0.5)

    conn.close()
    logger.info(f"[batch] Done — {success} scored, {failed} failed")


if __name__ == "__main__":
    run_batch_processor()
