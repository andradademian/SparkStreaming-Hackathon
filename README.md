# World Cup 2026 — Bluesky Firehose (Spark Streaming Hackathon)

Real-time ingestion and analysis of World Cup / football posts from the
[Bluesky Jetstream](https://docs.bsky.app/blog/jetstream) firehose, processed
with PySpark and visualised with Streamlit + Plotly.

---

## Architecture

```
Bluesky Jetstream (WebSocket)
        │
        ▼
 ┌─────────────────┐   TCP :9999   ┌──────────────────────────────┐
 │  producer.ipynb │ ────────────► │       consumer.ipynb         │
 │                 │               │  ingestion │  Spark metrics  │
 │                 │               │  TCP recv  │  TF-IDF / agg   │
 │ • keyword filter│               │  micro-    │  windowed agg   │
 │ • parse schema  │               │  batches   │  CSV metrics    │
 │ • broadcast TCP │               │  → Parquet │  → CSV metrics  │
 └─────────────────┘               └────────────┴────────┬────────┘
                                                          │
                                                          ▼
                                                   viz_app.py
                                                (Streamlit dashboard)
```

## Data schema

Every post forwarded from producer → consumer has this shape:

| Field        | Type         | Description                           |
|--------------|--------------|---------------------------------------|
| `did`        | string       | Author's decentralised identifier     |
| `post_uri`   | string       | `at://` URI of the post               |
| `text`       | string       | Full post text                        |
| `created_at` | string (ISO) | Timestamp set by the author's client  |
| `ingested_at`| string (ISO) | Timestamp when the producer saw it    |
| `reply_to`   | string\|null | Parent post URI (if a reply)          |
| `mentions`   | string[]     | DIDs of mentioned users               |
| `urls`       | string[]     | External links embedded in the post   |
| `hashtags`   | string[]     | Hashtags extracted via regex          |
| `lang`       | string\|null | First declared language code          |

## Metrics produced

| File                                   | Contents                                      |
|----------------------------------------|-----------------------------------------------|
| `data/metrics/post_volume.csv`         | Post count per 60 s / 5 s sliding window      |
| `data/metrics/mention_counts.csv`      | Mention occurrences per window                |
| `data/metrics/url_counts.csv`          | URL occurrences per window                    |
| `data/metrics/tfidf_top10.csv`         | Top-10 TF-IDF keywords across the corpus      |
| `data/metrics/hashtag_counts.csv`      | Hashtag leaderboard (top 20)                  |
| `data/metrics/lang_dist.csv`           | Language distribution                         |
| `data/metrics/sentiment_over_time.csv` | Avg VADER compound score per window (optional)|
| `data/metrics/snapshot.png`            | Static chart saved at last run                |

Spark temp views registered for ad-hoc SQL: `raw`, `post_volume`,
`mention_counts`, `url_counts`, `tfidf_top10`, `hashtag_counts`, `lang_dist`,
`sentiment_over_time` (if vaderSentiment is installed).

---

## Prerequisites

- Docker Desktop
- The `pyspark_container` image (includes Jupyter Lab, PySpark, Java)

Optional — install inside the container:

```bash
pip install vaderSentiment     # enables sentiment analysis
pip install streamlit plotly   # needed for viz_app.py
```

---

## How to run

### 1  Start the container

```bash
docker run -it -p 4040:4040 -p 8080:8080 -p 8081:8081 -p 8888:8888 -p 5432:5432 --cpus=2 --memory=2048m -v '//c/Users/yourname/yourfolder/:/mnt/host_home/' -h spark -w /mnt/host_home/ pyspark_container jupyter-lab --ip 0.0.0.0 --port 8888 --no-browser --allow-root
```

Open Jupyter at **http://localhost:8888**.

### 2  Run the producer

Open **`producer.ipynb`** and run all cells top-to-bottom.

The last cell (`await listen_and_produce()`) streams indefinitely — leave it running.

### 3  Run the consumer

Open **`consumer.ipynb`** in a **second browser tab**.

**Ingestion cells (0 – 4):** run top-to-bottom.
Cell 4 (micro-batch loop) also runs indefinitely — leave it running.
Let it collect at least a few batches before continuing.

**Processing cells (5 – 13):** run top-to-bottom in a separate execution
(open the notebook in a second kernel, or interrupt cell 4, then run the processing cells).
Re-run any time to refresh metrics from the accumulated Parquet data.

### 4  Launch the Streamlit dashboard (optional)

In a terminal inside the container:

```bash
pip install streamlit plotly
streamlit run viz_app.py --server.port 8501
```

Open **http://localhost:8501**.
The dashboard polls `./data/metrics/` and auto-refreshes on the interval you
set in the sidebar. Re-running the processing cells writes fresh CSVs which the
dashboard picks up on its next refresh.

---

## Ports

| Port | Service                    |
|------|----------------------------|
| 8888 | Jupyter Lab                |
| 4040 | Spark UI (jobs / stages)   |
| 8080 | Spark Master UI            |
| 8081 | Spark Worker UI            |
| 8501 | Streamlit dashboard        |
| 9999 | Producer → Consumer TCP    |
