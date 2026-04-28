#1226906709 - Om Patel

from fastapi import FastAPI, Query, HTTPException
from neo4j import GraphDatabase
from typing import List
import os

app = FastAPI(
    title="NeoFlow NYC API",
    description="Graph analytics API for NYC Bronx taxi trip data",
    version="1.0.0"
)

# ── Neo4j connection ──────────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "processingpipeline")

def getDriver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def closeDriver(driver):
    driver.close()

# ── Neo4j query runners ───────────────────────────────────────────────────────
def runPageRankQuery(session, maxIterations: int, weightProperty: str):
    return session.run("""
        CALL gds.pageRank.stream('pr_graph', {
            maxIterations: $maxIter,
            dampingFactor: 0.85,
            relationshipWeightProperty: $weightProp
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, score
        ORDER BY score DESC
    """, maxIter=maxIterations, weightProp=weightProperty)

def runBfsQuery(session, startNode: int, targetIds: List[int]):
    return session.run("""
        MATCH (source:Location {name: $start})
        MATCH (targets:Location) WHERE targets.name IN $targets
        WITH source, collect(id(targets)) AS targetIds
        CALL gds.bfs.stream('bfs_graph', {
            sourceNode: id(source),
            targetNodes: targetIds
        })
        YIELD path
        RETURN [n IN nodes(path) | n.name] AS path
    """, start=startNode, targets=targetIds)

# ── Graph projection helpers ──────────────────────────────────────────────────
def projectPageRankGraph(session, weightProperty: str):
    session.run("CALL gds.graph.drop('pr_graph', false)").consume()
    session.run("""
        CALL gds.graph.project(
            'pr_graph',
            'Location',
            { TRIP: { properties: $weightProp } }
        )
    """, weightProp=weightProperty).consume()

def projectBfsGraph(session):
    session.run("CALL gds.graph.drop('bfs_graph', false)").consume()
    session.run("""
        CALL gds.graph.project('bfs_graph', 'Location', 'TRIP')
    """).consume()

def dropPageRankGraph(session):
    session.run("CALL gds.graph.drop('pr_graph', false)").consume()

def dropBfsGraph(session):
    session.run("CALL gds.graph.drop('bfs_graph', false)").consume()

# ── Result formatters ─────────────────────────────────────────────────────────
def formatPageRankResults(result):
    return [{"name": record["name"], "score": round(record["score"], 6)} for record in result]

def formatBfsResults(result):
    rows = []
    for record in result:
        rows.append({"path": record["path"]})
    return rows

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def healthCheck():
    driver = getDriver()
    try:
        driver.verify_connectivity()
        return {"status": "ok", "neo4j": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unreachable: {str(e)}")
    finally:
        closeDriver(driver)

@app.get("/pagerank")
def pageRank(
    maxIterations: int = Query(default=20, ge=1, le=100, description="Number of PageRank iterations"),
    weightProperty: str = Query(default="distance", description="Relationship weight property: 'distance' or 'fare'")
):
    if weightProperty not in ["distance", "fare"]:
        raise HTTPException(status_code=400, detail="weightProperty must be 'distance' or 'fare'")

    driver = getDriver()
    try:
        with driver.session() as session:
            projectPageRankGraph(session, weightProperty)
            try:
                result = runPageRankQuery(session, maxIterations, weightProperty)
                data = formatPageRankResults(result)
            finally:
                dropPageRankGraph(session)
        return {
            "maxIterations": maxIterations,
            "weightProperty": weightProperty,
            "totalZones": len(data),
            "results": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        closeDriver(driver)

@app.get("/bfs")
def bfs(
    startNode: int = Query(description="Starting taxi zone ID"),
    targets: str  = Query(description="Comma-separated target zone IDs, e.g. 212,167,78")
):
    targetIds = []
    try:
        targetIds = [int(t.strip()) for t in targets.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="targets must be comma-separated integers")

    driver = getDriver()
    try:
        with driver.session() as session:
            projectBfsGraph(session)
            try:
                result = runBfsQuery(session, startNode, targetIds)
                data = formatBfsResults(result)
            finally:
                dropBfsGraph(session)
        return {
            "startNode": startNode,
            "targets": targetIds,
            "paths": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        closeDriver(driver)

@app.get("/zones")
def getAllZones():
    driver = getDriver()
    try:
        with driver.session() as session:
            result = session.run("MATCH (n:Location) RETURN n.name AS name ORDER BY n.name")
            zones = [record["name"] for record in result]
        return {"totalZones": len(zones), "zones": zones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        closeDriver(driver)