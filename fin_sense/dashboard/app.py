import os 
import requests

import streamlit as st 
import pandas as pd
import numpy as np 
import plotly.express as px 
import plotly.graph_objects as go 

st.set_page_config(page_title= "FinSense", page_icon = "📈", layout = "wide")

API_BASE ="http://localhost:8000"

def fetch(endpoint: str, params: dict= None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params= params, timeout= 5)
        r.raise_for_status()
        return r.json()

    except Exception as e:
        st.error(f"API error: {e}")
        return None
    


def prediction_color(label: str) -> str:
    return {"UP": "🟢", "DOWN": "🔴", "FLAT": "🟡"}.get(label, "⚪")


st.title(f"📈 FinSense — Personal Finance Intelligence")
st.caption(f"Real-time news sentiment + market movement predictions for Indian investors")

st.divider()

st.subheader("Today's Predictions")

predictions = fetch("/predictions")

if predictions:

    df_pred = pd.DataFrame(predictions)
    df_pred = df_pred.drop_duplicates(subset="asset", keep= "first")

    cols = st.columns(3)
    for i , asset in enumerate(["NIFTY","GOLD","CRYPTO"]):
        row = df_pred[df_pred["asset"] == asset]
        with cols[i]:
            if not row.empty:
                label = row["predicted_label"].values[0]
                confidence = float(row["confidence"].values[0])
                st.metric(
                    label=f"{prediction_color(label)} {asset}",
                    value=label,
                    delta=f"Confidence: {confidence:.0%}"
                )

            else:
                st.metric(label=asset, value="No data", delta="—")  
else:
    st.info("No predictions yet — run the pipeline first.")


st.divider()
st.subheader("Sentiment Trend (Last 7 days)")

asset_filter = st.selectbox("Select asset", ["nifty", "gold", "crypto"], index=0)

trend = fetch("/sentiment/trend", params={"asset": asset_filter, "days": 7})


if trend and len(trend) > 0:
    df_trend = pd.DataFrame(trend)

    fig = px.bar(
        df_trend, 
        x= "date",
        y= "avg_sentiment",
        color= "avg_sentiment",
        color_continuous_scale=["red", "yellow", "green"],
        range_color=[-1, 1],
        labels={"avg_sentiment": "Avg Sentiment", "date": "Date"},
        title=f"{asset_filter.upper()} sentiment over last 7 days"
    )

    fig.update_layout(
        showlegend=False,
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"No sentiment data yet for {asset_filter.upper()} in the last 7 days.")


st.divider()


# News Feed 
st.subheader("Latetst News With Sentiment")

news_asset = st.selectbox("FIlter by asset",
                          ["all", "nifty", "gold", "crypto", "rbi", "general"],
                          index=0)

params = {"limit": 15}

if news_asset != "all":
    params["asset"] = news_asset

news = fetch("/news",params= params)

if news:
    for article in news:
        label = article.get("sentiment_label", "neutral")
        score = article.get("sentiment_score",0) or 0
        icon = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(label, "⚪")
        impact = article.get("impact","low") or "low"


        with st.expander(f"{icon} {article['headline'][:90]}..."):
            col1,col2,col3 = st.columns(3)
            col1.metric("Sentiment",label.upper(),f"{score:+.2f}")
            col2.metric("Impact", impact.upper())
            col3.metric("Asset", article.get("asset_tag", "—").upper())

            if article.get("explanation"):
                st.info(f"💡 {article['explanation']}")

            st.caption(
                f"Source: {article.get('source','—')} | "
                f"Published: {article.get('published_at','—')}"
            )

else:
    st.info("No News Article Found")

st.divider()

stats = fetch("/stats")
if stats:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Articles",  stats["total_articles"])
    c2.metric("Scored Articles", stats["scored_articles"])
    c3.metric("Price Rows",      stats["total_prices"])
    c4.metric("Predictions",     stats["predictions"])

st.caption("FinSense — built with Python, Groq, XGBoost, FastAPI, Streamlit")

