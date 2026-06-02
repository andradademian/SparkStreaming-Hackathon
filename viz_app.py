"""
Live-updating Streamlit dashboard for the World Cup 2026 Firehose.

Run:
    pip install streamlit plotly
    streamlit run viz_app.py
"""
import os
import time
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

METRICS_DIR = "./data/metrics"

st.set_page_config(
    page_title="World Cup 2026 Firehose",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ World Cup 2026 — Bluesky Firehose Dashboard")
st.caption("Metrics are read from ./data/metrics/. Re-run the processing cells in consumer.ipynb to refresh.")

refresh_sec = st.sidebar.slider("Auto-refresh interval (s)", 5, 120, 15)
st.sidebar.markdown("---")
st.sidebar.markdown("**Views available**")
st.sidebar.markdown("- Post volume\n- TF-IDF keywords\n- Top mentions\n- Top hashtags\n- Sentiment\n- Language breakdown")


def load(name: str) -> pd.DataFrame | None:
    path = os.path.join(METRICS_DIR, f"{name}.csv")
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def render():
    # ── Row 1: post volume + TF-IDF ──────────────────────────────────────────
    col1, col2 = st.columns(2)

    pv = load("post_volume")
    if pv is not None:
        pv["window_start"] = pd.to_datetime(pv["window_start"])
        with col1:
            st.subheader("Post Volume Over Time")
            fig = px.bar(
                pv, x="window_start", y="post_count",
                labels={"window_start": "Window start", "post_count": "Posts"},
                color_discrete_sequence=["steelblue"],
            )
            fig.update_layout(margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        col1.info("No post_volume data yet.")

    tw = load("tfidf_top10")
    if tw is not None:
        tw = tw.sort_values("tfidf", ascending=True)
        with col2:
            st.subheader("TF-IDF Top-10 Keywords")
            fig = px.bar(
                tw, x="tfidf", y="word", orientation="h",
                labels={"tfidf": "TF-IDF score", "word": ""},
                color="tfidf", color_continuous_scale="Reds",
            )
            fig.update_layout(margin=dict(t=20), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        col2.info("No tfidf_top10 data yet.")

    # ── Row 2: mentions + hashtags ────────────────────────────────────────────
    col3, col4 = st.columns(2)

    mc = load("mention_counts")
    if mc is not None:
        top_m = (
            mc.groupby("mention", as_index=False)["occurrences"]
            .sum()
            .nlargest(10, "occurrences")
            .sort_values("occurrences", ascending=True)
        )
        with col3:
            st.subheader("Top 10 Mentioned Users")
            fig = px.bar(
                top_m, x="occurrences", y="mention", orientation="h",
                labels={"occurrences": "Mentions", "mention": ""},
                color_discrete_sequence=["seagreen"],
            )
            fig.update_layout(margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        col3.info("No mention_counts data yet.")

    hc = load("hashtag_counts")
    if hc is not None:
        top_h = hc.nlargest(10, "occurrences").sort_values("occurrences", ascending=True)
        with col4:
            st.subheader("Top 10 Hashtags")
            fig = px.bar(
                top_h, x="occurrences", y="hashtag", orientation="h",
                labels={"occurrences": "Count", "hashtag": ""},
                color_discrete_sequence=["mediumpurple"],
            )
            fig.update_layout(margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        col4.info("No hashtag_counts data yet.")

    # ── Row 3: sentiment + language ───────────────────────────────────────────
    col5, col6 = st.columns(2)

    sot = load("sentiment_over_time")
    if sot is not None:
        sot["window_start"] = pd.to_datetime(sot["window_start"])
        with col5:
            st.subheader("Sentiment Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sot["window_start"], y=sot["avg_sentiment"],
                mode="lines+markers", line=dict(color="#f9a825"),
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray",
                          annotation_text="neutral")
            fig.update_layout(
                yaxis=dict(title="Avg compound score", range=[-1, 1]),
                xaxis_title="Window start",
                margin=dict(t=20),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        col5.info("No sentiment data (run: pip install vaderSentiment, then re-run cell B-Optional).")

    ld = load("lang_dist")
    if ld is not None:
        top_l = ld.dropna(subset=["lang"]).nlargest(10, "post_count")
        with col6:
            st.subheader("Language Distribution (top 10)")
            fig = px.pie(top_l, values="post_count", names="lang",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        col6.info("No lang_dist data yet.")

    st.caption(f"Last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")


render()
time.sleep(refresh_sec)
st.rerun()
