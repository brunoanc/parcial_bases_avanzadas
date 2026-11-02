"""Reúne las consultas Cypher de vecinos, dependencias y rutas vulnerables."""

# Consultar solo las dependencias directas
NEIGHBORS = """
MATCH (n {id: $id})-[:DEPENDS_ON]->(p:PackageVersion)
WHERE (n:Project OR n:PackageVersion)
RETURN p {.*} AS node ORDER BY p.name, p.version
"""

# Reunir los nodos alcanzables y sus conexiones sin repetir caminos
GRAPH = """
MATCH (project:Project {id: $id})
OPTIONAL MATCH (project)-[:DEPENDS_ON*1..]->(package:PackageVersion)
WITH project, collect(DISTINCT package) AS packages
UNWIND [project] + packages AS source
OPTIONAL MATCH (source)-[relation:DEPENDS_ON|AFFECTED_BY]->(target)
RETURN collect(DISTINCT source) + collect(DISTINCT target) AS nodes,
       collect(DISTINCT relation) AS edges
"""

# Buscar todos los caminos hacia versiones vulnerables
ANALYSIS = """
MATCH path = (p:Project {id: $id})-[:DEPENDS_ON*1..]->
(pkg:PackageVersion)-[:AFFECTED_BY]->(v:Vulnerability)
RETURN v {.*} AS vulnerability, pkg {.*} AS package,
       length(path) - 1 AS dependencyDepth,
       [n IN nodes(path) | n.id] AS pathNodeIds,
       [r IN relationships(path) | {
           source: startNode(r).id, target: endNode(r).id, type: type(r)
       }] AS pathEdges
ORDER BY dependencyDepth, vulnerability.id, package.id, pathNodeIds
"""
