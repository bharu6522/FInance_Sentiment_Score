import os 
import logging
from dotenv import load_dotenv 
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)
client = Groq(api_key= os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a friendly personal finance advisor for everyday Indians.

Given a news headline and its sentiment, explain in 2 simple sentences
what this news means for a retail investor — someone who has a SIP,
fixed deposit, or small crypto holding.

Use plain language. No jargon. Be direct and specific.
Example: "This is good news for your debt mutual funds. 
The RBI keeping rates steady means your SIP returns stay stable 
and there is no pressure on bond prices."

"""

def explain_headline(headline: str, sentiment_label : str, asset_tag: str)-> str|None:

    try:
        response = client.chat.completions.create(
            model = "llama-3.1-8b-instant",
            messages= [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Headline: {headline}\n"
                    f"Sentiment: {sentiment_label}\n"
                    f"Asset: {asset_tag}" )}, 
                    ],
            temperature=0.4,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e :
        logger.error(f"[explainer] Failed: {e}")
        return None
    


if __name__ == "__main__":
    tests = [
        ("RBI holds repo rate at 6.5%", "positive", "rbi"),
        ("Nifty crashes 500 points as FII selling intensifies", "negative", "nifty"),
        ("Gold prices hit all-time high amid global uncertainty", "positive", "gold"),
    
        ]

    for headline, label, asset  in tests:
        print(f"\nHeadline : {headline}")
        explanation = explain_headline(headline, label, asset)
        print(f"Explains : {explanation}")

