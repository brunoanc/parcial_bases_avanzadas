import { authorization } from "./auth";
import { baseUrl } from "./config";

export type Kind = "projects" | "packages" | "vulnerabilities";

export interface DependencyTarget {
    kind: "projects" | "packages";
    id: string;
    dependencyId?: string;
}

export type NodeType = "Project" | "PackageVersion" | "Vulnerability";

export interface GraphNode {
    id: string;
    type?: NodeType;
    name?: string;
    description?: string;
    version?: string;
    ecosystem?: string;
    severity?: string;
    cvssScore?: number | null;
    cvssVector?: string | null;
    sourceUrl?: string | null;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface Finding {
    vulnerability: GraphNode;
    package: GraphNode;
    dependencyDepth: number;
    pathNodeIds: string[];
    pathEdgeIds: string[];
    pathEdges: GraphEdge[];
}

export interface Analysis {
    findings: Finding[];
}

export interface Neighbors {
    packages: GraphNode[];
    vulnerabilities: GraphNode[];
}

export const severityLabels: Record<string, string> = {
    critical: "Crítica",
    high: "Alta",
    medium: "Media",
    low: "Baja"
};

const fieldLabels: Record<string, string> = {
    name: "Nombre",
    description: "Descripción",
    version: "Versión",
    ecosystem: "Ecosistema",
    id: "Identificador",
    severity: "Severidad",
    cvssScore: "Puntuación CVSS",
    cvssVector: "Vector CVSS",
    sourceUrl: "Fuente",
    sourceType: "Origen",
    sourceId: "Origen",
    targetPackageId: "Paquete destino",
    packageId: "Paquete",
    vulnerabilityId: "Vulnerabilidad"
};

function validationMessage(issue: { loc: (string | number)[]; type: string }): string {
    const field = fieldLabels[String(issue.loc[issue.loc.length - 1])] || "Campo";
    const messages: Record<string, string> = {
        missing: "Completa este campo.",
        string_too_short: "Escribe un valor más largo.",
        string_too_long: "El valor es demasiado largo.",
        string_pattern_mismatch: "Revisa el formato.",
        literal_error: "Selecciona una opción válida.",
        extra_forbidden: "Este campo no está permitido.",
        string_type: "Escribe un texto válido.",
        json_invalid: "El contenido no es válido."
    };

    return `${field}: ${messages[issue.type] || "Revisa el valor."}`;
}

export async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    let response: Response;
    const headers: Record<string, string> = body ? { "Content-Type": "application/json" } : {};

    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        headers.Authorization = await authorization();
    }

    try {
        response = await fetch(`${baseUrl}${path}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
            signal: AbortSignal.timeout(30000)
        });
    }
    catch {
        throw new Error("No se pudo cargar el espacio de trabajo. Revisa tu conexión e intenta de nuevo.");
    }

    if (!response.ok) {
        if (response.status === 503) {
            throw new Error(
                "El espacio de trabajo no está disponible por el momento. Intenta de nuevo en unos minutos."
            );
        }

        const error = await response.json().catch(() => null);
        const message = Array.isArray(error?.detail)
            ? error.detail.map(validationMessage).join(" · ")
            : error?.detail === "Not Found"
              ? "No se encontró el registro."
              : error?.detail;
        throw new Error(message || "No se pudo completar la solicitud.");
    }

    return response.status === 204 ? (undefined as T) : response.json();
}

export function nodeLabel(node: GraphNode): string {
    return node.version ? `${node.name}@${node.version}` : node.name || node.id;
}

export function nodePath(kind: Kind, id: string): string {
    return `/${kind}/${encodeURIComponent(id)}`;
}
