"""
Build a single-file interactive dashboard from data/metrics/*.csv.

Output: data/metrics/dashboard.html — open in any browser, no server required.
Uses Plotly (CDN-hosted) for charts.
"""
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot

METRICS_DIR = os.path.join(os.path.dirname(__file__), "data", "metrics")
OUT_PATH = os.path.join(METRICS_DIR, "dashboard.html")


def load(name):
    path = os.path.join(METRICS_DIR, f"{name}.csv")
    return pd.read_csv(path) if os.path.exists(path) else None


def to_div(fig):
    return plot(fig, include_plotlyjs="cdn", output_type="div")


charts = []

# Post volume
pv = load("post_volume")
if pv is not None and len(pv):
    pv["window_start"] = pd.to_datetime(pv["window_start"])
    fig = px.bar(pv, x="window_start", y="post_count",
                 title="Post volume (60 s windows, 5 s slide)",
                 labels={"window_start": "Window start", "post_count": "Posts"},
                 color_discrete_sequence=["steelblue"])
    fig.update_layout(height=380)
    charts.append(to_div(fig))

# TF-IDF
tw = load("tfidf_top10")
if tw is not None and len(tw):
    tw_sorted = tw.sort_values("tfidf", ascending=True)
    fig = px.bar(tw_sorted, x="tfidf", y="word", orientation="h",
                 title="TF-IDF top-10 keywords across the corpus",
                 labels={"tfidf": "TF-IDF score", "word": ""},
                 color="tfidf", color_continuous_scale="Reds")
    fig.update_layout(height=380, coloraxis_showscale=False)
    charts.append(to_div(fig))

# Top mentions
mc = load("mention_counts")
if mc is not None and len(mc):
    top_m = (mc.groupby("mention", as_index=False)["occurrences"]
             .sum().nlargest(10, "occurrences").sort_values("occurrences"))
    fig = px.bar(top_m, x="occurrences", y="mention", orientation="h",
                 title="Top 10 mentioned users (DIDs)",
                 labels={"occurrences": "Mentions", "mention": ""},
                 color_discrete_sequence=["seagreen"])
    fig.update_layout(height=380)
    charts.append(to_div(fig))

# Top referenced posts
prc = load("post_reference_counts")
if prc is not None and len(prc):
    top_r = (prc.groupby("ref_post", as_index=False)["occurrences"]
             .sum().nlargest(10, "occurrences").sort_values("occurrences"))
    top_r["short"] = top_r["ref_post"].str.slice(-25)
    fig = px.bar(top_r, x="occurrences", y="short", orientation="h",
                 title="Top 10 referenced posts (last 25 chars of URI)",
                 labels={"occurrences": "References", "short": ""},
                 color_discrete_sequence=["#c2410c"])
    fig.update_layout(height=380)
    charts.append(to_div(fig))

# Top URLs
uc = load("url_counts")
if uc is not None and len(uc):
    top_u = (uc.groupby("url", as_index=False)["occurrences"]
             .sum().nlargest(10, "occurrences").sort_values("occurrences"))
    top_u["short"] = top_u["url"].str.slice(0, 60)
    fig = px.bar(top_u, x="occurrences", y="short", orientation="h",
                 title="Top 10 external URLs",
                 labels={"occurrences": "Shares", "short": ""},
                 color_discrete_sequence=["#0369a1"])
    fig.update_layout(height=380)
    charts.append(to_div(fig))

# Hashtags
hc = load("hashtag_counts")
if hc is not None and len(hc):
    top_h = hc.nlargest(10, "occurrences").sort_values("occurrences")
    fig = px.bar(top_h, x="occurrences", y="hashtag", orientation="h",
                 title="Top 10 hashtags",
                 labels={"occurrences": "Count", "hashtag": ""},
                 color_discrete_sequence=["mediumpurple"])
    fig.update_layout(height=380)
    charts.append(to_div(fig))

# Sentiment over time (optional)
sot = load("sentiment_over_time")
if sot is not None and len(sot):
    sot["window_start"] = pd.to_datetime(sot["window_start"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sot["window_start"], y=sot["avg_sentiment"],
                             mode="lines+markers", line=dict(color="#f9a825")))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="neutral")
    fig.update_layout(title="Average sentiment per window (VADER compound)",
                      yaxis=dict(title="Score", range=[-1, 1]),
                      xaxis_title="Window start", height=380)
    charts.append(to_div(fig))

# Language distribution
ld = load("lang_dist")
if ld is not None and len(ld):
    top_l = ld.dropna(subset=["lang"]).nlargest(10, "post_count")
    fig = px.pie(top_l, values="post_count", names="lang",
                 title="Language distribution (top 10)",
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(height=380)
    charts.append(to_div(fig))

html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>World Cup 2026 Firehose — Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 24px; background:#fafafa; color:#222; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color:#666; margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .card {{ background:#fff; border:1px solid #e5e5e5; border-radius:8px;
             padding:8px; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
    @media (max-width: 1000px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>⚽ World Cup 2026 — Bluesky Firehose Dashboard</h1>
  <p class="sub">Team: Bojan Ivanovski, Andrada Demian · Built from <code>data/metrics/*.csv</code></p>
  <div class="grid">
    {''.join(f'<div class="card">{c}</div>' for c in charts)}
  </div>
</body>
</html>
"""

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1024:.1f} KB)")
