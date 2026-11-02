"""Define las rutas HTTP, el inicio de la API y las respuestas de error."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from neo4j.exceptions import AuthError, ConstraintError, Neo4jError, ServiceUnavailable, SessionExpired

from .db import Database
from .repository import Repository
from .schemas import (
    AnalysisResponse,
    GraphResponse,
    HealthResponse,
    NeighborsResponse,
    Project,
    Package,
    Vulnerability,
    AffectedInput,
    DependencyInput,
    PackageInput,
    ProjectInput,
    ProjectPatch,
    VulnerabilityInput,
    VulnerabilityPatch,
)

logger = logging.getLogger("dependencyguard")

# Definir los errores comunes de las rutas
RESOURCE_ERRORS = {
    404: {"description": "Nodo inexistente"},
    409: {"description": "Identificador duplicado o ciclo"},
    503: {"description": "AuraDB no disponible"},
}


# Abrir la conexión al iniciar y cerrarla al terminar
@asynccontextmanager
async def lifespan(app):
    app.state.db = Database()
    app.state.repository = Repository(app.state.db)

    # Mantener la conexión abierta mientras funciona la API
    try:
        yield
    finally:
        # Cerrar la conexión aunque ocurra un error
        app.state.db.close()


# Preparar la API y sus rutas
app = FastAPI(
    title="DependencyGuard API",
    version="1.0.0",
    lifespan=lifespan,
    description="Análisis de dependencias npm y CVEs documentados con CVSS. Sin límite de profundidad o cantidad de rutas. Sin autenticación; uso académico local.",
)

# Permitir peticiones desde la interfaz local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


# Responder los errores de la base sin mostrar datos privados
@app.exception_handler(Neo4jError)
@app.exception_handler(ServiceUnavailable)
@app.exception_handler(SessionExpired)
async def database_error(request, error):
    # Distinguir un identificador duplicado de otros errores
    if isinstance(error, ConstraintError) or getattr(error, "code", "").endswith(
        "ConstraintValidationFailed"
    ):
        return JSONResponse(status_code=409, content={"detail": "Ya existe un nodo con ese identificador."})

    # Avisar cuando AuraDB rechaza las credenciales
    if isinstance(error, AuthError):
        message = "Neo4j rechazó las credenciales. Revisa el archivo .env."
    else:
        # Preparar la respuesta para el caso restante
        message = "No se pudo consultar Neo4j AuraDB. Revisa la conexión e intenta de nuevo."

    logger.error("Failed to query AuraDB: %s", type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": message})


# Obtener las operaciones de la base para esta petición
def repo(request: Request):
    return request.app.state.repository


# Comprobar que AuraDB responde
@app.get("/health", tags=["System"], response_model=HealthResponse)
def health(request: Request):
    request.app.state.db.query("RETURN 1 AS ok")
    return {"status": "ok", "database": "AuraDB"}


# Consultar el grafo del proyecto
@app.get(
    "/projects/{node_id}/graph",
    tags=["Explorer"],
    response_model=GraphResponse,
    response_model_exclude_none=True,
)
def graph(node_id: str, request: Request):
    return repo(request).graph(node_id)


# Buscar caminos hacia versiones vulnerables
@app.get("/projects/{node_id}/analysis", tags=["Explorer"], response_model=AnalysisResponse)
def analysis(node_id: str, request: Request):
    return repo(request).analysis(node_id)


# Consultar los paquetes directos del proyecto
@app.get("/projects/{node_id}/neighbors", tags=["Explorer"], response_model=NeighborsResponse)
def project_neighbors(node_id: str, request: Request):
    return repo(request).neighbors("projects", node_id)


# Consultar las dependencias y los CVEs del paquete
@app.get("/packages/{node_id:path}/neighbors", tags=["Explorer"], response_model=NeighborsResponse)
def package_neighbors(node_id: str, request: Request):
    return repo(request).neighbors("packages", node_id)


# Crear o reemplazar una dependencia
@app.post("/dependencies", status_code=204, tags=["Relations"])
def add_dependency(body: DependencyInput, request: Request):
    repo(request).dependency(body)
    return Response(status_code=204)


# Quitar una dependencia
@app.delete("/dependencies", status_code=204, tags=["Relations"])
def remove_dependency(body: DependencyInput, request: Request):
    repo(request).dependency(body, remove=True)
    return Response(status_code=204)


# Asociar un CVE con una versión
@app.post("/affected-by", status_code=204, tags=["Relations"])
def add_affected(body: AffectedInput, request: Request):
    repo(request).affected(body)
    return Response(status_code=204)


# Quitar la asociación con el CVE
@app.delete("/affected-by", status_code=204, tags=["Relations"])
def remove_affected(body: AffectedInput, request: Request):
    repo(request).affected(body, remove=True)
    return Response(status_code=204)


# Consultar los proyectos
@app.get(
    "/projects",
    tags=["Projects"],
    response_model=list[Project],
    operation_id="list_projects",
    responses=RESOURCE_ERRORS,
)
def list_projects(request: Request):
    return repo(request).list("projects")


# Crear el proyecto
@app.post(
    "/projects",
    tags=["Projects"],
    response_model=Project,
    status_code=201,
    operation_id="create_projects",
    responses=RESOURCE_ERRORS,
)
def create_project(body: ProjectInput, request: Request):
    return repo(request).create("projects", body)


# Buscar el proyecto
@app.get(
    "/projects/{node_id:path}",
    tags=["Projects"],
    response_model=Project,
    operation_id="get_projects",
    responses=RESOURCE_ERRORS,
)
def get_project(node_id: str, request: Request):
    return repo(request).get("projects", node_id)


# Actualizar el proyecto
@app.patch(
    "/projects/{node_id:path}",
    tags=["Projects"],
    response_model=Project,
    operation_id="patch_projects",
    responses=RESOURCE_ERRORS,
)
def update_project(node_id: str, body: ProjectPatch, request: Request):
    return repo(request).update("projects", node_id, body)


# Eliminar el proyecto
@app.delete(
    "/projects/{node_id:path}",
    tags=["Projects"],
    status_code=204,
    operation_id="delete_projects",
    responses=RESOURCE_ERRORS,
)
def delete_project(node_id: str, request: Request):
    repo(request).delete("projects", node_id)
    return Response(status_code=204)


# Consultar las versiones
@app.get(
    "/packages",
    tags=["Packages"],
    response_model=list[Package],
    operation_id="list_packages",
    responses=RESOURCE_ERRORS,
)
def list_packages(request: Request):
    return repo(request).list("packages")


# Crear la versión
@app.post(
    "/packages",
    tags=["Packages"],
    response_model=Package,
    status_code=201,
    operation_id="create_packages",
    responses=RESOURCE_ERRORS,
)
def create_package(body: PackageInput, request: Request):
    return repo(request).create("packages", body)


# Buscar la versión
@app.get(
    "/packages/{node_id:path}",
    tags=["Packages"],
    response_model=Package,
    operation_id="get_packages",
    responses=RESOURCE_ERRORS,
)
def get_package(node_id: str, request: Request):
    return repo(request).get("packages", node_id)


# Actualizar la versión
@app.patch(
    "/packages/{node_id:path}",
    tags=["Packages"],
    response_model=Package,
    operation_id="patch_packages",
    responses=RESOURCE_ERRORS,
)
def update_package(node_id: str, body: PackageInput, request: Request):
    return repo(request).update("packages", node_id, body)


# Eliminar la versión
@app.delete(
    "/packages/{node_id:path}",
    tags=["Packages"],
    status_code=204,
    operation_id="delete_packages",
    responses=RESOURCE_ERRORS,
)
def delete_package(node_id: str, request: Request):
    repo(request).delete("packages", node_id)
    return Response(status_code=204)


# Consultar los CVEs
@app.get(
    "/vulnerabilities",
    tags=["Vulnerabilities"],
    response_model=list[Vulnerability],
    operation_id="list_vulnerabilities",
    responses=RESOURCE_ERRORS,
)
def list_vulnerabilities(request: Request):
    return repo(request).list("vulnerabilities")


# Crear el CVE
@app.post(
    "/vulnerabilities",
    tags=["Vulnerabilities"],
    response_model=Vulnerability,
    status_code=201,
    operation_id="create_vulnerabilities",
    responses=RESOURCE_ERRORS,
)
def create_vulnerability(body: VulnerabilityInput, request: Request):
    return repo(request).create("vulnerabilities", body)


# Buscar el CVE
@app.get(
    "/vulnerabilities/{node_id:path}",
    tags=["Vulnerabilities"],
    response_model=Vulnerability,
    operation_id="get_vulnerabilities",
    responses=RESOURCE_ERRORS,
)
def get_vulnerability(node_id: str, request: Request):
    return repo(request).get("vulnerabilities", node_id)


# Actualizar el CVE
@app.patch(
    "/vulnerabilities/{node_id:path}",
    tags=["Vulnerabilities"],
    response_model=Vulnerability,
    operation_id="patch_vulnerabilities",
    responses=RESOURCE_ERRORS,
)
def update_vulnerability(node_id: str, body: VulnerabilityPatch, request: Request):
    return repo(request).update("vulnerabilities", node_id, body)


# Eliminar el CVE
@app.delete(
    "/vulnerabilities/{node_id:path}",
    tags=["Vulnerabilities"],
    status_code=204,
    operation_id="delete_vulnerabilities",
    responses=RESOURCE_ERRORS,
)
def delete_vulnerability(node_id: str, request: Request):
    repo(request).delete("vulnerabilities", node_id)
    return Response(status_code=204)
