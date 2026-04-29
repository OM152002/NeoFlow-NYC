# NeoFlow NYC 🚕 → 🗃️ → 📊

A graph data pipeline built around NYC Yellow Taxi trip data — starting with a Dockerized Neo4j setup, evolving into a full Kubernetes streaming architecture with Kafka, and finishing with a REST API and interactive map dashboard.

This was a three-phase project for CSE 511 (Data Processing at Scale) at Arizona State University.

---

## What's the idea?

New York City taxi trips are basically a graph problem. Every neighborhood is a node, every trip is an edge, and the data tells you a lot about how the city actually moves. This project takes the March 2022 NYC Yellow Taxi dataset, filters it down to Bronx trips, and turns it into a property graph in Neo4j — then runs PageRank and BFS on top of it.

The interesting part is the infrastructure evolution. Phase 1 is simple and self-contained (one Docker image, everything baked in). Phase 2 tears that apart and rebuilds it as a live streaming pipeline on Kubernetes. Phase 3 puts a REST API and interactive map dashboard on top.

---

## Tech Stack

| Layer | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Database | Neo4j (Docker) | Neo4j (Helm on Kubernetes) | Same |
| Data ingestion | Python script at build time | Kafka + Neo4j Sink Connector | Same |
| Messaging | — | Apache Kafka + Zookeeper | Same |
| Orchestration | Docker | Kubernetes (Minikube) | Same |
| Graph algorithms | Neo4j GDS (PageRank, BFS) | Same | Same |
| API layer | — | — | FastAPI |
| Dashboard | — | — | Streamlit + Folium |
| Language | Python | Python | Python |

---

## Phase 1: Dockerized Neo4j

The goal here was simple: get the data into Neo4j inside a reproducible container, no manual steps.

**Graph Schema**

Every unique taxi zone becomes a `Location` node. Every trip becomes a `TRIP` relationship between two zones carrying distance, fare, and timestamps.

```
(Location)-[:TRIP {distance, fare, pickup_dt, dropoff_dt}]->(Location)
```

Filtering to Bronx zones gives us 42 nodes and 1,530 relationships from the March 2022 dataset.

**What the Dockerfile does**
- Downloads the NYC Taxi parquet file
- Installs Neo4j with the Graph Data Science (GDS) plugin
- Runs `data_loader.py` at build time to populate the graph
- Exposes ports 7474 (browser) and 7687 (Bolt)

**Algorithms implemented in `interface.py`**

*PageRank* — ranks each taxi zone by importance based on how many trips flow into it, weighted by distance or fare. Returns the highest and lowest ranked zones.

*BFS* — finds the shortest path between a start zone and one or more target zones through the trip graph.

**Running it**

```bash
docker build -t neoflow-phase1 .
docker run -d -p 7474:7474 -p 7687:7687 --name neoflow neoflow-phase1

# Wait ~2 minutes for Neo4j to start, and then run python3 tester.py:
```

---

## Phase 2: Kubernetes Streaming Pipeline

Phase 2 replaces the static Docker build with a live pipeline. Instead of loading data at build time, a Python producer streams trip records to Kafka, and a connector picks them up and writes them into Neo4j in real time.

**Architecture**

```
Python Producer
      |
      v
 Kafka Topic (nyc_taxicab_data)
      |
      v
Neo4j Kafka Sink Connector
      |
      v
   Neo4j (via Helm)
      |
      v
 PageRank / BFS via interface.py
```

**Components**

- **Zookeeper:** manages Kafka broker coordination (`zookeeper-setup.yaml`)
- **Kafka:** message broker with two listener ports: 9092 for external access, 29092 for internal pod communication (`kafka-setup.yaml`)
- **Neo4j:** deployed via the official Helm chart with GDS plugin enabled (`neo4j-values.yaml`, `neo4j-service.yaml`)
- **Kafka-Neo4j Connector:** consumes messages from the Kafka topic and writes them to Neo4j using a Cypher template (`kafka-neo4j-connector.yaml`)
- **data_producer.py:** reads the parquet file, filters to Bronx trips, and streams 1,530 JSON records to Kafka

**Running it**

```bash
minikube start --driver=docker --memory=6144 --cpus=4

kubectl apply -f zookeeper-setup.yaml
kubectl apply -f kafka-setup.yaml
helm install my-neo4j-release neo4j/neo4j -f neo4j-values.yaml
kubectl apply -f neo4j-service.yaml
kubectl apply -f kafka-neo4j-connector.yaml

kubectl get pods -w

kubectl port-forward svc/neo4j-service 7474:7474 7687:7687
kubectl port-forward svc/kafka-service 9092:9092

python3 data_producer.py
python3 tester.py
```

---

## Phase 3: REST API + Interactive Dashboard

Phase 3 exposes the graph analytics as a REST API and wraps it in an interactive map dashboard built with Streamlit and Folium.

**Architecture**

```
Neo4j (Kubernetes)
      |
      v
FastAPI (REST API)
  ├── GET /health
  ├── GET /pagerank?maxIterations=20&weightProperty=distance
  ├── GET /bfs?startNode=159&targets=212,167
  └── GET /zones
      |
      v
Streamlit Dashboard
  ├── PageRank Tab — color-graduated circle map of Bronx zones
  └── BFS Tab — interactive path finder with route visualization
```

**API Endpoints**

| Endpoint | Description |
|---|---|
| `GET /health` | Check Neo4j connectivity |
| `GET /pagerank` | Run PageRank with configurable iterations and weight |
| `GET /bfs` | Find BFS path between zones |
| `GET /zones` | List all 42 Bronx zone IDs |

**Dashboard Features**

- **PageRank map:** each Bronx zone shown as a circle. Bigger and warmer = higher PageRank. Hover for zone name and score.
- **BFS path finder:** pick a start and target zone(s), get the shortest path drawn on the map with numbered stops and a dashed route line.
- Results persist across widget interactions via Streamlit session state.

**Running it**

```bash
#Neo4j port-forward (Kubernetes must be running)
kubectl port-forward svc/neo4j-service 7474:7474 7687:7687

#FastAPI
cd Phase_3/APIs
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

#Streamlit
cd Phase_3/dashboard
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Results

| Phase | Score |
|---|---|
| Phase 1 — Data loading + algorithms | 60/60 (tester) |
| Phase 2 — Full Kubernetes pipeline | 100/100 |
| Phase 3 — API + Dashboard | 100% Fully functional |

---

## Dataset

[NYC TLC Yellow Taxi Trip Data — March 2022](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

Filtered to Bronx pickup and dropoff zones only. The parquet file is not included in this repo (53MB) — download it separately.

---

## Notes

- Neo4j takes 2-3 minutes to fully start after the pod shows Running.
- The Kafka connector needs ~2500Mi of memory for the JVM — don't lower that limit.
- Kafka message retention is 24 hours. If testing the next day, re-run the producer first.
- The Neo4j Helm chart labels pods as `app=my-neo4j-release` — service selector must match exactly.
- The GDS plugin ships inside the Neo4j container at `/var/lib/neo4j/products/` and is copied to plugins via a lifecycle postStart hook on every pod start.
