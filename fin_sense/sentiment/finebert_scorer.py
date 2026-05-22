import os 
import json 
import time 
import logging
from groq import Groq 
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
client = Groq(api_key = os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a financial analyst specialized in Indian markets.

Given a news headline, return ONLY a valid JSON object with exactly these fields:
{
  "sentiment_label": "positive" or "negative" or "neutral",
  "sentiment_score": a float between -1.0 (very negative) and +1.0 (very positive),
  "asset_tag": one of "nifty" or "gold" or "crypto" or "rbi" or "general",
  "impact": "low" or "medium" or "high",
  "reason": a single sentence explaining why
}

Rules:
- Return ONLY the JSON. No explanation, no markdown, no extra text.
- sentiment_score must match sentiment_label directionally.
  positive → score between 0.1 and 1.0
  negative → score between -1.0 and -0.1
  neutral  → score between -0.1 and 0.1
- impact is how much this news affects retail investors in India.


"""

def score_headline(headline: str,retries: int=3) -> dict | None:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Headline: {headline}"}
                ],
                temperature=0.1,   # low temp = consistent structured output
                max_tokens=200,
            )

            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)
            required = ["sentiment_label", "sentiment_score", "asset_tag",
                        "impact", "reason"]
            if not all(k in result for k in required):
                raise ValueError(f"Missing fields in response: {raw}")

            return result

        except json.JSONDecodeError as e:

            logger.warning(f"[scorer] JSON parse failed attempt {attempt+1}: {e}")
            time.sleep(1)

        except Exception as e:
            logger.warning(f"[scorer] Attempt {attempt+1} failed: {e}")
            time.sleep(2)

    
    logger.error(f"[scorer] All retries failed for: {headline}")
    return None


if __name__ == "__main__":
    # quick test
    test_headlines = [
        "RBI holds repo rate at 6.5%, signals pause in rate cycle",
        "Nifty crashes 500 points as FII selling intensifies",
        "Gold prices hit all-time high amid global uncertainty",
        "Bitcoin drops 10% after US SEC crackdown on exchanges",
        "Infosys reports strong Q3 results, raises guidance",
    ]

    for headline in test_headlines:
        print(f"\nHeadline: {headline}")
        result = score_headline(headline)
        if result:
            print(f"  Label  : {result['sentiment_label']}")
            print(f"  Score  : {result['sentiment_score']}")
            print(f"  Asset  : {result['asset_tag']}")
            print(f"  Impact : {result['impact']}")
            print(f"  Reason : {result['reason']}")
        else:
            print("  FAILED to score")
