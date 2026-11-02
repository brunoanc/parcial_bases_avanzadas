"""Configura la conexión con AuraDB y ejecuta consultas y transacciones."""

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from fastapi import HTTPException

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


# Mantener la conexión con AuraDB
class Database:
    # Leer las credenciales y preparar el driver oficial
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "")
        username = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        self.name = os.getenv("NEO4J_DATABASE") or None
        self.driver = None

        # Abrir la conexión cifrada cuando haya credenciales
        if uri.startswith("neo4j+s://") and username and password:
            self.driver = GraphDatabase.driver(
                uri, auth=(username, password), connection_timeout=10, connection_acquisition_timeout=15
            )

    # Revisar que la conexión esté configurada
    def require_driver(self):
        # Avisar si faltan las credenciales de conexión
        if self.driver is None:
            raise HTTPException(503, "Configura las credenciales de Neo4j AuraDB en .env.")

        return self.driver

    # Ejecutar una consulta con parámetros
    def query(self, query, **parameters):
        result = self.require_driver().execute_query(query, parameters_=parameters, database_=self.name)
        return [record.data() for record in result.records]

    # Ejecutar los cambios dentro de una transacción
    def write(self, operation):
        # Cerrar la sesión al terminar la transacción
        with self.require_driver().session(database=self.name) as session:
            return session.execute_write(operation)

    # Evitar identificadores repetidos por tipo de nodo
    def constraints(self):
        # Crear una restricción para cada tipo de nodo
        for label in ("Project", "PackageVersion", "Vulnerability"):
            self.query(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )

    # Cerrar la conexión con AuraDB
    def close(self):
        # Cerrar solo si se abrió una conexión
        if self.driver:
            self.driver.close()
