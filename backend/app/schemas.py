"""Define y valida los datos que recibe y devuelve la API."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


# Limpiar los textos y rechazar campos desconocidos
class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Validar los datos de un proyecto
class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


# Validar los cambios parciales de un proyecto
class ProjectPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    # Rechazar campos obligatorios con valor null
    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, values):
        # Dejar que Pydantic rechace un cuerpo que no sea un objeto
        if not isinstance(values, dict):
            return values

        # Revisar cada campo recibido antes de aplicar los cambios
        for value in values.values():
            # Conservar los valores obligatorios
            if value is None:
                raise ValueError("Los campos no pueden ser null.")

        return values


# Validar una versión de paquete
class PackageInput(Input):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9@._/-]+$")
    version: str = Field(min_length=1, max_length=60, pattern=r"^[a-zA-Z0-9._+-]+$")
    ecosystem: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9-]+$")

    # Unir ecosistema, nombre y versión en un identificador
    @property
    def package_id(self):
        return f"{self.ecosystem}:{self.name}@{self.version}"


Severity = Literal["critical", "high", "medium", "low"]


# Validar la puntuación y la fuente del CVE
class CvssFields(Input):
    cvssScore: float | None = Field(default=None, ge=0, le=10)
    cvssVector: str | None = Field(default=None, max_length=200)
    sourceUrl: str | None = Field(default=None, pattern=r"^https://", max_length=500)


# Validar los datos de un CVE
class VulnerabilityInput(CvssFields):
    id: str = Field(pattern=r"^(CVE-\d{4}-\d{4,}|DEMO-[A-Z0-9-]+)$", max_length=60)
    severity: Severity
    description: str = Field(min_length=1, max_length=2000)


# Validar los cambios parciales de un CVE
class VulnerabilityPatch(CvssFields):
    severity: Severity | None = None
    description: str | None = Field(default=None, min_length=1, max_length=2000)

    # Rechazar campos obligatorios con valor null
    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, values):
        # Dejar que Pydantic rechace un cuerpo que no sea un objeto
        if not isinstance(values, dict):
            return values

        # Permitir limpiar los campos CVSS, pero no los datos obligatorios
        for field in ("severity", "description"):
            # Evitar que se borre un dato obligatorio
            if field in values and values[field] is None:
                raise ValueError("Los campos no pueden ser null.")

        return values


# Validar el origen y destino de una dependencia
class DependencyInput(Input):
    sourceType: Literal["project", "package"]
    sourceId: str = Field(min_length=1, max_length=250)
    targetPackageId: str = Field(min_length=1, max_length=250)
    replacePackageId: str | None = Field(default=None, min_length=1, max_length=250)


# Validar la asociación entre paquete y CVE
class AffectedInput(Input):
    packageId: str = Field(min_length=1, max_length=250)
    vulnerabilityId: str = Field(min_length=1, max_length=60)


# Incluir el identificador del proyecto en la respuesta
class Project(ProjectInput):
    id: str


# Incluir el identificador de la versión en la respuesta
class Package(PackageInput):
    id: str


# Usar los datos del CVE como respuesta
class Vulnerability(VulnerabilityInput):
    pass


# Definir los datos de un nodo del mapa
class GraphNode(BaseModel):
    id: str
    type: Literal["Project", "PackageVersion", "Vulnerability"]
    name: str | None = None
    version: str | None = None
    ecosystem: str | None = None
    description: str | None = None
    severity: Severity | None = None
    cvssScore: float | None = None
    cvssVector: str | None = None
    sourceUrl: str | None = None


# Definir el origen, destino y tipo de relación
class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["DEPENDS_ON", "AFFECTED_BY"]


# Devolver los nodos y relaciones del mapa
class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# Describir una ruta hacia una vulnerabilidad
class Finding(BaseModel):
    vulnerability: Vulnerability
    package: Package
    dependencyDepth: int
    pathNodeIds: list[str]
    pathEdgeIds: list[str]
    pathEdges: list[GraphEdge]


# Devolver todas las rutas del análisis
class AnalysisResponse(BaseModel):
    findings: list[Finding]


# Devolver los paquetes y CVEs vecinos
class NeighborsResponse(BaseModel):
    packages: list[Package]
    vulnerabilities: list[Vulnerability]


# Confirmar que la conexión está disponible
class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["AuraDB"]
