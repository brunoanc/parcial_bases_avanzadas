"""Lee el dataset JSON y carga los nodos y relaciones iniciales en AuraDB."""

import json
from pathlib import Path

from backend.app.db import Database

# Leer los nodos y dependencias preparados para la demostración
DATA = Path(__file__).resolve().parents[1] / "data/seed.json"
dataset = json.loads(DATA.read_text())
PROJECTS = dataset["projects"]
PACKAGES = dataset["packages"]
DEPENDENCIES = dataset["dependencies"]
VULNERABILITIES = []
AFFECTED = []

# Separar los datos del CVE de sus versiones afectadas
for advisory in dataset["advisories"]:
    vulnerability = {
        "id": advisory["id"],
        "severity": advisory["severity"],
        "description": advisory["description"],
        "cvssScore": advisory["cvssScore"],
        "cvssVector": advisory["cvssVector"],
        "sourceUrl": advisory["sourceUrl"],
    }
    VULNERABILITIES.append(vulnerability)

    # Asociar cada versión afectada con el CVE
    for package in advisory["affectedPackages"]:
        package_id = f"npm:{package['name']}@{package['version']}"
        AFFECTED.append({"package": package_id, "vulnerability": advisory["id"]})


# Cargar los nodos y sus relaciones sin duplicarlos
def populate(tx):
    catalogs = {"Project": PROJECTS, "PackageVersion": PACKAGES, "Vulnerability": VULNERABILITIES}

    # Guardar juntos los nodos de cada tipo
    for label, nodes in catalogs.items():
        tx.run(
            f"UNWIND $nodes AS values MERGE (n:{label} {{id: values.id}}) SET n += values",
            nodes=nodes,
        ).consume()

    # Conectar los proyectos y versiones con sus dependencias
    tx.run(
        """
        UNWIND $edges AS edge
        MATCH (s {id: edge.source}), (t:PackageVersion {id: edge.target})
        WHERE s:Project OR s:PackageVersion
        MERGE (s)-[:DEPENDS_ON]->(t)
        """,
        edges=DEPENDENCIES,
    ).consume()

    # Conectar las versiones afectadas con sus CVEs
    tx.run(
        """
        UNWIND $edges AS edge
        MATCH (p:PackageVersion {id: edge.package}), (v:Vulnerability {id: edge.vulnerability})
        MERGE (p)-[:AFFECTED_BY]->(v)
        """,
        edges=AFFECTED,
    ).consume()


# Crear las restricciones y cargar los datos iniciales
def seed(db):
    db.constraints()
    db.write(populate)


# Cargar los datos al ejecutar este módulo
if __name__ == "__main__":
    db = Database()

    # Usar la conexión solo durante la carga
    try:
        seed(db)
        print(f"Seed listo: {len(PROJECTS)} proyectos, {len(PACKAGES)} versiones y {len(VULNERABILITIES)} CVEs.")
    finally:
        # Cerrar la conexión aunque ocurra un error
        db.close()
