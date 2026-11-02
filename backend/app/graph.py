"""Convierte los resultados de Neo4j en datos para el mapa y el análisis."""

import json


# Identificar la relación por su origen, tipo y destino
def edge_id(source, target, kind):
    return json.dumps([source, kind, target], ensure_ascii=False, separators=(",", ":"))


# Preparar una relación para la interfaz
def edge_data(source, target, kind):
    return {"id": edge_id(source, target, kind), "source": source, "target": target, "type": kind}


# Convertir los nodos y relaciones de Neo4j a datos para la interfaz
def serialize_graph(record):
    nodes = {}
    edges = []

    # Unir los nodos encontrados como origen o destino de una conexión
    for node in record["nodes"]:
        values = dict(node)

        # Identificar el tipo del nodo por su etiqueta
        for label in ("Project", "PackageVersion", "Vulnerability"):
            if label in node.labels:
                values["type"] = label
                break

        nodes[node["id"]] = values

    # Preparar las conexiones únicas que devuelve la consulta
    for relation in record["edges"]:
        edge = edge_data(relation.start_node["id"], relation.end_node["id"], relation.type)
        edges.append(edge)

    return {"nodes": list(nodes.values()), "edges": edges}


# Preparar todas las rutas sin recortar los resultados
def serialize_analysis(records):
    findings = []

    # Convertir cada ruta del análisis
    for record in records:
        edges = [edge_data(edge["source"], edge["target"], edge["type"]) for edge in record["pathEdges"]]
        finding = record.copy()
        finding["pathEdgeIds"] = [edge["id"] for edge in edges]
        finding["pathEdges"] = edges
        findings.append(finding)

    return {"findings": findings}
