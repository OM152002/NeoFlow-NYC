#1226906709 - Om Patel

from neo4j import GraphDatabase

class Interface:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        self._driver.verify_connectivity()

    def close(self):
        self._driver.close()

    def bfs(self, start_node, last_node):

        if not isinstance(last_node, list):
            last_node = [last_node]
 
        with self._driver.session() as session:
            session.run("CALL gds.graph.drop('bfs_graph', false)").consume()
 
            session.run("""
                CALL gds.graph.project(
                    'bfs_graph',
                    'Location',
                    'TRIP'
                )
            """).consume()
 
            try:
                result = session.run("""
                    MATCH (source:Location {name: $start})
                    MATCH (targets:Location) WHERE targets.name IN $targets
                    WITH source, collect(id(targets)) AS targetIds
                    CALL gds.bfs.stream('bfs_graph', {
                        sourceNode: id(source),
                        targetNodes: targetIds
                    })
                    YIELD path
                    RETURN [n IN nodes(path) | {name: n.name}] AS path
                """, start=start_node, targets=last_node)
 
                rows = [{"path": record["path"]} for record in result]
            finally:
                session.run("CALL gds.graph.drop('bfs_graph', false)").consume()
 
        return rows

        raise NotImplementedError

    def pagerank(self, max_iterations, weight_property):
        
        with self._driver.session() as session:
            session.run("CALL gds.graph.drop('pr_graph', false)").consume()
 
            session.run("""
                CALL gds.graph.project(
                    'pr_graph',
                    'Location',
                    {
                        TRIP: {
                            properties: $weightProp
                        }
                    }
                )
            """, weightProp=weight_property).consume()
 
            try:
                result = session.run("""
                    CALL gds.pageRank.stream('pr_graph', {
                        maxIterations: $maxIter,
                        dampingFactor: 0.85,
                        relationshipWeightProperty: $weightProp
                    })
                    YIELD nodeId, score
                    RETURN gds.util.asNode(nodeId).name AS name, score AS score
                    ORDER BY score DESC
                """, maxIter=max_iterations, weightProp=weight_property)
 
                rows = [{"name": record["name"], "score": record["score"]} for record in result]
            finally:
                session.run("CALL gds.graph.drop('pr_graph', false)").consume()
 
        if not rows:
            return []
 
        return [rows[0], rows[-1]]

        raise NotImplementedError

