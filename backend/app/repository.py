"""Implementa las operaciones de nodos y relaciones sobre Neo4j."""

from uuid import uuid4

from fastapi import HTTPException
from .graph import serialize_analysis, serialize_graph
from .queries import ANALYSIS, GRAPH, NEIGHBORS

# Usar solo las etiquetas conocidas al formar las consultas
LABELS = {"projects": "Project", "packages": "PackageVersion", "vulnerabilities": "Vulnerability"}


# Agrupar las operaciones de nodos y relaciones
class Repository:
    # Guardar la conexión que usan las consultas
    def __init__(self, db):
        self.db = db

    # Consultar los nodos del catálogo
    def list(self, kind):
        label = LABELS[kind]
        rows = self.db.query(
            f"MATCH (n:{label}) RETURN n {{.*}} AS node ORDER BY coalesce(n.name, n.id), n.id"
        )
        return [row["node"] for row in rows]

    # Buscar un nodo por su identificador
    def get(self, kind, node_id):
        rows = self.db.query(f"MATCH (n:{LABELS[kind]} {{id: $id}}) RETURN n {{.*}} AS node", id=node_id)

        # Avisar si el nodo no existe
        if not rows:
            raise HTTPException(404, "No se encontró el nodo.")

        return rows[0]["node"]

    # Crear un nodo con sus datos
    def create(self, kind, body):
        values = body.model_dump()

        # Asignar un identificador al nuevo proyecto
        if kind == "projects":
            values["id"] = str(uuid4())
        # Tratar los datos propios de una versión de paquete
        elif kind == "packages":
            values["id"] = body.package_id

        rows = self.db.query(
            f"CREATE (n:{LABELS[kind]}) SET n = $values RETURN n {{.*}} AS node", values=values
        )
        return rows[0]["node"]

    # Actualizar el nodo sin perder otras versiones
    def update(self, kind, node_id, body):
        values = body.model_dump(exclude_unset=True)

        # Exigir al menos un cambio
        if not values:
            raise HTTPException(422, "Indica al menos un campo para actualizar.")

        # Tratar los datos propios de una versión de paquete
        if kind == "packages":
            # Revisar que exista la versión original
            self.get(kind, node_id)
            new_id = body.package_id

            # Guardar la nueva versión sin cambiar la original
            if new_id != node_id:
                rows = self.db.query(
                    "MERGE (n:PackageVersion {id: $id}) SET n += $values RETURN n {.*} AS node",
                    id=new_id,
                    values=values,
                )
                return rows[0]["node"]

        rows = self.db.query(
            f"MATCH (n:{LABELS[kind]} {{id: $id}}) SET n += $values RETURN n {{.*}} AS node",
            id=node_id,
            values=values,
        )

        # Avisar si el nodo no existe
        if not rows:
            raise HTTPException(404, "No se encontró el nodo.")

        return rows[0]["node"]

    # Eliminar el nodo y sus relaciones
    def delete(self, kind, node_id):
        rows = self.db.query(
            f"MATCH (n:{LABELS[kind]} {{id: $id}}) DETACH DELETE n RETURN count(*) AS deleted", id=node_id
        )

        # Avisar si no se encontró un nodo para eliminar
        if not rows[0]["deleted"]:
            raise HTTPException(404, "No se encontró el nodo.")

    # Consultar las conexiones directas del nodo
    def neighbors(self, kind, node_id):
        self.get(kind, node_id)
        rows = self.db.query(NEIGHBORS, id=node_id)
        packages = [row["node"] for row in rows]
        vulnerabilities = []

        # Consultar también los CVEs asociados a la versión
        if kind == "packages":
            rows = self.db.query(
                "MATCH (:PackageVersion {id: $id})-[:AFFECTED_BY]->(v:Vulnerability) RETURN v {.*} AS node ORDER BY v.id",
                id=node_id,
            )
            vulnerabilities = [row["node"] for row in rows]

        return {"packages": packages, "vulnerabilities": vulnerabilities}

    # Crear, quitar o reemplazar una dependencia
    def dependency(self, body, remove=False):
        label = "Project" if body.sourceType == "project" else "PackageVersion"

        # Guardar la relación en una sola transacción
        def save(tx):
            nodes = tx.run(
                f"MATCH (s:{label} {{id: $source}}), (t:PackageVersion {{id: $target}}) RETURN s.id, t.id",
                source=body.sourceId,
                target=body.targetPackageId,
            ).single()

            # Comprobar que existan ambos extremos de la relación
            if not nodes:
                raise HTTPException(404, "No se encontró el origen o el paquete destino.")

            # Impedir ciclos al conectar dos paquetes
            if not remove and body.sourceType == "package":
                # Bloquear las versiones en orden antes de comprobar el ciclo
                # Así dos peticiones no aprueban al mismo tiempo caminos incompatibles
                tx.run("""
                    MATCH (n:PackageVersion)
                    WITH n ORDER BY n.id
                    SET n.id = n.id
                    """).consume()
                cycle = tx.run(
                    """
                    MATCH (t:PackageVersion {id: $target}), (s:PackageVersion {id: $source})
                    RETURN t = s OR EXISTS {
                        MATCH (t)-[:DEPENDS_ON*1..]->(s)
                    } AS cycle
                    """,
                    source=body.sourceId,
                    target=body.targetPackageId,
                ).single()

                # Rechazar la relación si forma un ciclo
                if cycle["cycle"]:
                    raise HTTPException(409, "La dependencia crearía un ciclo.")

            # Revisar la dependencia que será reemplazada
            if body.replacePackageId and not remove:
                old = tx.run(
                    f"MATCH (s:{label} {{id: $source}})-[:DEPENDS_ON]->(t:PackageVersion {{id: $old}}) RETURN t.id",
                    source=body.sourceId,
                    old=body.replacePackageId,
                ).single()

                # Avisar si la dependencia anterior ya no existe
                if not old:
                    raise HTTPException(404, "No se encontró la dependencia que se intenta reemplazar.")

                # Quitar la versión anterior antes de conectar la nueva
                if body.replacePackageId != body.targetPackageId:
                    tx.run(
                        f"MATCH (s:{label} {{id: $source}})-[r:DEPENDS_ON]->(:PackageVersion {{id: $old}}) DELETE r",
                        source=body.sourceId,
                        old=body.replacePackageId,
                    ).consume()

            # Elegir la operación sobre la relación
            if remove:
                action = "MATCH (s)-[r:DEPENDS_ON]->(t) DELETE r"
            else:
                action = "MERGE (s)-[:DEPENDS_ON]->(t)"
            tx.run(
                f"MATCH (s:{label} {{id: $source}}), (t:PackageVersion {{id: $target}}) {action}",
                source=body.sourceId,
                target=body.targetPackageId,
            ).consume()

        self.db.write(save)

    # Vincular o desvincular un paquete y un CVE
    def affected(self, body, remove=False):
        # Guardar la relación en una sola transacción
        def save(tx):
            nodes = tx.run(
                "MATCH (p:PackageVersion {id: $package}), (v:Vulnerability {id: $vulnerability}) RETURN p.id",
                package=body.packageId,
                vulnerability=body.vulnerabilityId,
            ).single()

            # Comprobar que existan ambos extremos de la relación
            if not nodes:
                raise HTTPException(404, "No se encontró el paquete o la vulnerabilidad.")

            # Elegir la operación sobre la asociación al CVE
            if remove:
                action = "MATCH (p)-[r:AFFECTED_BY]->(v) DELETE r"
            else:
                action = "MERGE (p)-[:AFFECTED_BY]->(v)"
            tx.run(
                f"MATCH (p:PackageVersion {{id: $package}}), (v:Vulnerability {{id: $vulnerability}}) {action}",
                package=body.packageId,
                vulnerability=body.vulnerabilityId,
            ).consume()

        self.db.write(save)

    # Consultar el grafo del proyecto
    def graph(self, project_id):
        self.get("projects", project_id)
        result = self.db.require_driver().execute_query(GRAPH, id=project_id, database_=self.db.name)
        return serialize_graph(result.records[0])

    # Buscar caminos hacia versiones vulnerables
    def analysis(self, project_id):
        self.get("projects", project_id)
        return serialize_analysis(self.db.query(ANALYSIS, id=project_id))
