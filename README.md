# NeoFlow NYC 🚕 → 🗃️ → 📊

A graph data pipeline built around NYC Yellow Taxi trip data: Starting with a Dockerized Neo4j setup and evolving into a full Kubernetes streaming architecture with Kafka.

This was a two-phase project for CSE 511 (Data Processing at Scale) at Arizona State University. Phase 1 gets the data into a graph database. Phase 2 makes it stream in real time.

---

## What's the idea?

New York City taxi trips are basically a graph problem. Every neighborhood is a node, every trip is an edge, and the data tells you a lot about how the city actually moves. This project takes the March 2022 NYC Yellow Taxi dataset, filters it down to Bronx trips, and turns it into a property graph in Neo4j and then runs PageRank and BFS on top of it.

The interesting part is the infrastructure evolution. Phase 1 is simple and self-contained (one Docker image, everything baked in). Phase 2 tears that apart and rebuilds it as a live streaming pipeline on Kubernetes, where trip data flows from a Kafka topic into Neo4j in real time.

---

## Tech Stack

| Layer | Phase 1 | Phase 2 |
|---|---|---|
| Database | Neo4j (Docker) | Neo4j (Helm on Kubernetes) |
| Data ingestion | Python script at build time | Kafka + Neo4j Sink Connector |
| Messaging | — | Apache Kafka + Zookeeper |
| Orchestration | Docker | Kubernetes (Minikube) |
| Graph algorithms | Neo4j GDS (PageRank, BFS) | Same |
| Language | Python | Python |

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

*PageRank:* ranks each taxi zone by importance based on how many trips flow into it, weighted by distance or fare. Returns the highest and lowest ranked zones.

*BFS:* finds the shortest path between a start zone and one or more target zones through the trip graph.

Both use the Neo4j GDS library directly via Cypher.

**Running it**

```bash
docker build -t neoflow-phase1 .
docker run -d -p 7474:7474 -p 7687:7687 --name neoflow neoflow-phase1

# Wait ~2 minutes for Neo4j to start, then:
python3 tester.py
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
# Start minikube
minikube start --driver=docker --memory=6144 --cpus=4

# Deploy everything
kubectl apply -f zookeeper-setup.yaml
kubectl apply -f kafka-setup.yaml
helm install my-neo4j-release neo4j/neo4j -f neo4j-values.yaml
kubectl apply -f neo4j-service.yaml
kubectl apply -f kafka-neo4j-connector.yaml

# Wait for all pods to be Running
kubectl get pods -w

# Port forward (run in separate terminals)
kubectl port-forward svc/neo4j-service 7474:7474 7687:7687
kubectl port-forward svc/kafka-service 9092:9092

# Stream the data
python3 data_producer.py

# Run the tester
python3 tester.py
```

---

## Results

| Phase | Score |
|---|---|
| Phase 1 — Data loading + algorithms | 60/60 (tester) |
| Phase 2 — Full pipeline | 100/100 |

---

## Dataset

[NYC TLC Yellow Taxi Trip Data — March 2022](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

Filtered to Bronx pickup and dropoff zones only. The parquet file is not included in this repo (53MB); download it separately if you want to run it yourself.

---

## Notes

A few things worth knowing if you're trying to run this yourself:

- Neo4j takes 2-3 minutes to fully start after the pod shows Running. Be patient before running the tester.
- The Kafka connector needs ~2500Mi of memory for the JVM. Don't lower that limit or it'll OOMKill before starting.
- Kafka message retention is 24 hours by default. If you're testing the next day, re-run the producer before running the tester.
- The Neo4j Helm chart labels pods as `app=my-neo4j-release`. Make sure your service selector matches that exactly.
