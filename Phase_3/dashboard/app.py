import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from bronxZones import BRONX_ZONES

API_BASE = "http://localhost:8000"

# ── api ───────────────────────────────────────────────────────────────────────
def fetchPageRank(maxIterations: int, weightProperty: str) -> dict:
    response = requests.get(f"{API_BASE}/pagerank", params={"maxIterations": maxIterations, "weightProperty": weightProperty})
    response.raise_for_status()
    return response.json()

def fetchBfs(startNode: int, targets: str) -> dict:
    response = requests.get(f"{API_BASE}/bfs", params={"startNode": startNode, "targets": targets})
    response.raise_for_status()
    return response.json()

def fetchAllZones() -> list:
    response = requests.get(f"{API_BASE}/zones")
    response.raise_for_status()
    return response.json()["zones"]

# ── session state ─────────────────────────────────────────────────────────────
def initSessionState() -> None:
    if "pagerankData" not in st.session_state:
        st.session_state.pagerankData = None
    if "bfsData" not in st.session_state:
        st.session_state.bfsData = None
    if "bfsPath" not in st.session_state:
        st.session_state.bfsPath = None

def storePagerankResult(data: dict) -> None:
    st.session_state.pagerankData = data

def storeBfsResult(data: dict, path: list) -> None:
    st.session_state.bfsData = data
    st.session_state.bfsPath = path

def clearPagerankResult() -> None:
    st.session_state.pagerankData = None

def clearBfsResult() -> None:
    st.session_state.bfsData = None
    st.session_state.bfsPath = None

# ── data processing ───────────────────────────────────────────────────────────
def extractScores(results: list) -> list:
    return [r["score"] for r in results]

def computeNormalizedScore(score: float, minScore: float, scoreRange: float) -> float:
    return (score - minScore) / scoreRange if scoreRange else 0.0

def normalizeResults(results: list) -> list:
    scores = extractScores(results)
    minScore = min(scores)
    scoreRange = max(scores) - minScore
    return [(r["name"], r["score"], computeNormalizedScore(r["score"], minScore, scoreRange)) for r in results]

def extractPathFromResponse(data: dict) -> list:
    if not data["paths"]:
        return []
    return data["paths"][0]["path"]

def buildZoneOptions(zones: list) -> dict:
    return {f"Zone {z} — {BRONX_ZONES[z]['label']}" if z in BRONX_ZONES else f"Zone {z}": z for z in zones}

def buildTargetString(targetIds: list) -> str:
    return ",".join(str(t) for t in targetIds)

def resolveZoneLabel(zoneId: int) -> str:
    return BRONX_ZONES.get(zoneId, {}).get("label", "Unknown")

# ── color helpers ─────────────────────────────────────────────────────────────
def interpolateColor(normalized: float) -> str:
    r = int(30 + (220 - 30) * normalized)
    g = int(144 - (144 - 30) * normalized)
    b = int(255 - (255 - 30) * normalized)
    return f"#{r:02x}{g:02x}{b:02x}"

def resolveBfsNodeColor(index: int, pathLength: int) -> str:
    if index == 0:
        return "#2ecc71"
    if index == pathLength - 1:
        return "#e74c3c"
    return "#3498db"

def resolveBfsNodeLabel(index: int, pathLength: int) -> str:
    if index == 0:
        return "START"
    if index == pathLength - 1:
        return "END"
    return f"Stop {index}"

# ── map builders ──────────────────────────────────────────────────────────────
def buildBaseMap() -> folium.Map:
    return folium.Map(location=[40.855, -73.878], zoom_start=12, tiles="CartoDB positron")

def buildPageRankMarker(zoneId: int, score: float, normalized: float) -> folium.CircleMarker:
    zone = BRONX_ZONES[zoneId]
    color = interpolateColor(normalized)
    return folium.CircleMarker(
        location=[zone["lat"], zone["lon"]],
        radius=6 + normalized * 20,
        color=color, fill=True, fill_color=color, fill_opacity=0.8,
        tooltip=f"Zone {zoneId}: {zone['label']}<br>Score: {score:.4f}"
    )

def buildBfsMarker(zoneId: int, index: int, pathLength: int) -> folium.CircleMarker:
    zone = BRONX_ZONES[zoneId]
    color = resolveBfsNodeColor(index, pathLength)
    label = resolveBfsNodeLabel(index, pathLength)
    return folium.CircleMarker(
        location=[zone["lat"], zone["lon"]],
        radius=12, color=color, fill=True, fill_color=color, fill_opacity=0.9,
        tooltip=f"{label} — Zone {zoneId}: {zone['label']}"
    )

def buildBfsNumberIcon(index: int) -> folium.DivIcon:
    return folium.DivIcon(
        html=f'<div style="font-size:10px;font-weight:bold;color:white;">{index + 1}</div>',
        icon_size=(20, 20), icon_anchor=(10, 10)
    )

def buildPathLine(coords: list) -> folium.PolyLine:
    return folium.PolyLine(coords, color="#e67e22", weight=3, opacity=0.8, dash_array="8")

# ── map populators ────────────────────────────────────────────────────────────
def populatePageRankMap(fmap: folium.Map, normalizedResults: list) -> None:
    for zoneId, score, normalized in normalizedResults:
        if zoneId in BRONX_ZONES:
            buildPageRankMarker(zoneId, score, normalized).add_to(fmap)

def collectBfsCoords(path: list) -> list:
    return [[BRONX_ZONES[z]["lat"], BRONX_ZONES[z]["lon"]] for z in path if z in BRONX_ZONES]

def addBfsMarkers(fmap: folium.Map, path: list) -> None:
    for i, zoneId in enumerate(path):
        if zoneId not in BRONX_ZONES:
            continue
        zone = BRONX_ZONES[zoneId]
        buildBfsMarker(zoneId, i, len(path)).add_to(fmap)
        folium.Marker(location=[zone["lat"], zone["lon"]], icon=buildBfsNumberIcon(i)).add_to(fmap)

def populateBfsMap(fmap: folium.Map, path: list) -> None:
    addBfsMarkers(fmap, path)
    coords = collectBfsCoords(path)
    if len(coords) > 1:
        buildPathLine(coords).add_to(fmap)

# ── ui components ─────────────────────────────────────────────────────────────
def renderPageRankControls() -> tuple:
    maxIterations = st.slider("Max Iterations", min_value=5, max_value=100, value=20, step=5)
    weightProperty = st.radio("Weight Property", ["distance", "fare"])
    runClicked = st.button("Run PageRank", type="primary", use_container_width=True)
    return maxIterations, weightProperty, runClicked

def renderBfsControls(zoneOptions: dict) -> tuple:
    defaultStart = list(zoneOptions.values()).index(159) if 159 in zoneOptions.values() else 0
    defaultTargets = [k for k, v in zoneOptions.items() if v == 212]
    startLabel = st.selectbox("Start Zone", options=list(zoneOptions.keys()), index=defaultStart)
    targetLabels = st.multiselect("Target Zone(s)", options=list(zoneOptions.keys()), default=defaultTargets)
    runClicked = st.button("Find Path", type="primary", use_container_width=True)
    return startLabel, targetLabels, runClicked

def renderTopZones(results: list) -> None:
    st.markdown("#### Top 5 Zones")
    for i, z in enumerate(results[:5]):
        st.markdown(f"**{i+1}. Zone {z['name']}** — {resolveZoneLabel(z['name'])} `score: {z['score']:.4f}`")

def renderLowestZone(results: list) -> None:
    st.markdown("#### Lowest Ranked Zone")
    last = results[-1]
    st.markdown(f"**Zone {last['name']}** — {resolveZoneLabel(last['name'])} `score: {last['score']:.4f}`")

def renderBfsPath(path: list) -> None:
    st.markdown("#### Path")
    pathLabels = [f"Zone {z} ({resolveZoneLabel(z)})" for z in path]
    st.markdown(" → ".join(pathLabels))
    st.success(f"Path found with {len(path)} stop(s)")

def renderPageRankMap(data: dict) -> None:
    normalized = normalizeResults(data["results"])
    fmap = buildBaseMap()
    populatePageRankMap(fmap, normalized)
    st_folium(fmap, width=750, height=500, key="pagerankMap")
    st.markdown("---")
    renderTopZones(data["results"])
    renderLowestZone(data["results"])

def renderBfsMap(path: list) -> None:
    fmap = buildBaseMap()
    populateBfsMap(fmap, path)
    st_folium(fmap, width=750, height=500, key="bfsMap")
    st.markdown("---")
    renderBfsPath(path)

# ── tab renderers ─────────────────────────────────────────────────────────────
def renderPageRankTab() -> None:
    st.subheader("PageRank — Zone Importance Map")
    st.write("Bigger circles = more important zones based on incoming trip flow.")
    col1, col2 = st.columns([1, 3])
    with col1:
        maxIterations, weightProperty, runClicked = renderPageRankControls()
        if runClicked:
            with st.spinner("Running PageRank..."):
                try:
                    data = fetchPageRank(maxIterations, weightProperty)
                    storePagerankResult(data)
                except Exception as e:
                    st.error(f"API error: {e}")
                    clearPagerankResult()
    with col2:
        if st.session_state.pagerankData:
            renderPageRankMap(st.session_state.pagerankData)
        else:
            st_folium(buildBaseMap(), width=750, height=500, key="pagerankEmpty")
            st.info("Configure parameters and click Run PageRank.")

def renderBfsTab() -> None:
    st.subheader("BFS Path Finder — Route Between Zones")
    st.write("Find the shortest traversal path between Bronx taxi zones.")
    try:
        zones = fetchAllZones()
    except Exception:
        zones = list(BRONX_ZONES.keys())
    zoneOptions = buildZoneOptions(zones)
    col1, col2 = st.columns([1, 3])
    with col1:
        startLabel, targetLabels, runClicked = renderBfsControls(zoneOptions)
        if runClicked:
            if not targetLabels:
                st.warning("Please select at least one target zone.")
            else:
                startNode = zoneOptions[startLabel]
                targetIds = [zoneOptions[t] for t in targetLabels]
                with st.spinner("Running BFS..."):
                    try:
                        data = fetchBfs(startNode, buildTargetString(targetIds))
                        path = extractPathFromResponse(data)
                        storeBfsResult(data, path)
                    except Exception as e:
                        st.error(f"API error: {e}")
                        clearBfsResult()
    with col2:
        if st.session_state.bfsPath:
            renderBfsMap(st.session_state.bfsPath)
        elif st.session_state.bfsData is not None:
            st_folium(buildBaseMap(), width=750, height=500, key="bfsEmpty")
            st.warning("No path found between selected zones.")
        else:
            st_folium(buildBaseMap(), width=750, height=500, key="bfsEmpty")
            st.info("Select zones and click Find Path.")

# ── entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    st.title("🚕 NeoFlow NYC: Bronx Taxi Graph Analytics")
    st.caption("Real-time graph analytics on NYC Yellow Taxi trip data streamed via Kafka into Neo4j")
    initSessionState()
    tab1, tab2 = st.tabs(["📊 PageRank", "🗺️ BFS Path Finder"])
    with tab1:
        renderPageRankTab()
    with tab2:
        renderBfsTab()

if __name__ == "__main__":
    main()