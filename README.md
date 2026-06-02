# World Cup 2026 — Bluesky Firehose (Spark Streaming Hackathon)

**Team:** Bojan Ivanovski, Andrada Demian

Real-time ingestion and analysis of World Cup / football posts from the
[Bluesky Jetstream](https://docs.bsky.app/blog/jetstream) firehose, processed
with PySpark and visualised with Matplotlib (inline) and Streamlit + Plotly
(live dashboard).

---

## Architecture

```
Bluesky Jetstream (WebSocket)
        │
        ▼
 ┌─────────────────┐   TCP :9999   ┌──────────────────────────────┐
 │  producer.ipynb │ ────────────► │       consumer.ipynb         │
 │                 │               │  ingestion │  processing     │
 │ • regex filter  │               │  TCP recv  │  windowed agg   │
 │ • parse schema  │               │  micro-    │  TF-IDF         │
 │ • broadcast TCP │               │  batches   │  sentiment/lang │
 │                 │               │  → Parquet │  → CSV metrics  │
 └─────────────────┘               └────────────┴────────┬────────┘
                                                          │
                                                          ▼
                              ┌──────────────────────────────────┐
                              │  build_dashboard.py  → dashboard │
                              │                       .html      │
                              │  viz_app.py          (Streamlit, │
                              │                       optional)  │
                              └──────────────────────────────────┘
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

| File                                    | Contents                                          |
|-----------------------------------------|---------------------------------------------------|
| `data/metrics/metrics.csv`              | **Unified long-format view** of all windowed counters (post_volume, mention, post_reference, url) |
| `data/metrics/post_volume.csv`          | Post count per 60 s / 5 s sliding window          |
| `data/metrics/mention_counts.csv`       | User-mention occurrences per window               |
| `data/metrics/post_reference_counts.csv`| Replied-to post occurrences per window            |
| `data/metrics/url_counts.csv`           | External URL occurrences per window               |
| `data/metrics/tfidf_top10.csv`          | Top-10 TF-IDF keywords across the corpus          |
| `data/metrics/hashtag_counts.csv`       | Hashtag leaderboard (top 20)                      |
| `data/metrics/lang_dist.csv`            | Language distribution                             |
| `data/metrics/sentiment_over_time.csv`  | Avg VADER compound score per window (optional)    |
| `data/metrics/snapshot.png`             | Static 2 × 2 chart saved on each processing run   |

Spark temp views registered for ad-hoc SQL: **`raw`**, **`metrics`** (unified),
`post_volume`, `mention_counts`, `post_reference_counts`, `url_counts`,
`tfidf_top10`, `hashtag_counts`, `lang_dist`, `sentiment_over_time` (if
vaderSentiment is installed).

## Visualisations

| File                          | Type                       | How to view                  |
|-------------------------------|----------------------------|------------------------------|
| `data/metrics/snapshot.png`   | Static matplotlib 2 × 2    | Image viewer                 |
| `data/metrics/dashboard.html` | Standalone interactive HTML (Plotly, 8 charts) | Open in any browser |
| `viz_app.py`                  | Live-updating Streamlit dashboard | `streamlit run viz_app.py` |
| `build_dashboard.py`          | Regenerates `dashboard.html` from the CSVs | `python build_dashboard.py` |

---

## Prerequisites

- Docker Desktop
- The `pyspark_container` image — this is the **course-provided** PySpark
  container bundled with the hackathon kit (Jupyter Lab + PySpark 4.x + Java).
  No custom Dockerfile is shipped with this submission; we rely on the image
  the instructors distributed. If you need to rebuild it from scratch, any
  image that bundles JDK 17, Python 3.10+, PySpark 4.x and Jupyter Lab will
  work — see the `docker run` invocation below for the expected entrypoint.

Optional — install inside the container after it starts:

```bash
pip install vaderSentiment     # enables sentiment analysis
pip install streamlit plotly   # needed for viz_app.py
```

---

## How to run

### 1  Start the container

```bash
docker run -it \
  -p 4040:4040 -p 8080:8080 -p 8081:8081 -p 8888:8888 -p 5432:5432 \
  --cpus=2 --memory=2048m \
  -v '//c/Users/BojanIvanovski/Desktop/SparkStreaming-Hackathon/:/mnt/host_home/' \
  -h spark -w /mnt/host_home/ \
  pyspark_container \
  jupyter-lab --ip 0.0.0.0 --port 8888 --no-browser --allow-root
```

Open Jupyter at **http://localhost:8888**.

### 2  Run the producer

Open **`producer.ipynb`** and **Run → Run All Cells**.

Cell layout:

| Cell | Purpose |
|------|---------|
| 0    | Project header (team + description, markdown)              |
| 1    | `%pip install websockets pyspark`                          |
| 2    | Imports + strict word-boundary regex keyword filter        |
| 3    | `parse_event()` — Jetstream → schema                       |
| 4    | TCP socket server (background thread, port 9999)           |
| 5    | Bluesky Jetstream listener (`await listen_and_produce()`)  |

Cell 5 streams indefinitely — leave it running.

### 3  Run the consumer

Open **`consumer.ipynb`** in a **second browser tab**.

Cell layout:

| Cell  | Purpose |
|-------|---------|
| 0     | Project header (markdown)                                  |
| 1 – 4 | **Ingestion**: imports, Spark session, schema, TCP receiver thread |
| 5     | **Ingestion loop** — micro-batches every 5 s, appends Parquet, registers `raw` view (runs forever) |
| 6     | Processing section header (markdown)                       |
| 7 – 8 | Processing imports + `load_raw()`                          |
| 9     | Windowed aggregations (post_volume, mention_counts, post_reference_counts, url_counts) |
| 10    | TF-IDF top-10                                              |
| 11    | Optional metrics (VADER sentiment, hashtags, language, time range) |
| 12    | Unified `metrics` temp view + count by metric_type         |
| 13    | Save all metrics to CSV                                    |
| 14    | Inline 2 × 2 matplotlib snapshot → `snapshot.png`          |
| 15    | Ad-hoc SQL examples against the registered temp views      |

**How to drive it:** Run cells 1 – 5 top-to-bottom. Cell 5 runs forever — leave
it running. Wait until you have a few batches' worth of data, then run cells
7 – 15. You can re-run cells 7 – 15 any time to refresh metrics from the
accumulated Parquet data.

### 4  See the dashboard

Two options — pick one.

**4a. Standalone HTML (recommended, no extra server)**

From a terminal on the host (or inside the container):

```bash
pip install plotly pandas
python build_dashboard.py
```

Opens `data/metrics/dashboard.html` in any browser — 8 interactive Plotly
charts in a single self-contained file.

**4b. Live-updating Streamlit dashboard (optional)**

In a terminal inside the container:

```bash
pip install streamlit plotly
streamlit run viz_app.py --server.port 8501
```

Then open **http://localhost:8501** (requires `-p 8501:8501` on `docker run`).
Auto-refreshes on the interval set in the sidebar — re-running the processing
cells writes fresh CSVs that the dashboard picks up on its next tick.

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
