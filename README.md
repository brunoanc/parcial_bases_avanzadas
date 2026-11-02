# DependencyGuard

Aplicación para explorar dependencias entre proyectos y paquetes npm, identificar rutas a CVEs registrados y editar sus conexiones. Usa Svelte, FastAPI y Neo4j AuraDB.

## Requisitos

- Python 3.11 o posterior.
- Node.js 22.12 o posterior y npm.
- Una instancia de Neo4j AuraDB y conexión a Internet.

## Instalación

Ejecuta los comandos desde la raíz del proyecto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
npm --prefix frontend ci
cp .env.example .env
```

En `.env`, completa `NEO4J_URI`, `NEO4J_USERNAME` y `NEO4J_PASSWORD` con las credenciales de AuraDB. La URI debe comenzar con `neo4j+s://`. Deja `NEO4J_DATABASE` vacío para usar la base predeterminada y conserva `VITE_API_URL=http://127.0.0.1:8100`.

Carga los datos iniciales una vez:

```bash
.venv/bin/python -m backend.scripts.seed
```

## Ejecución

Inicia el backend en una terminal:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100
```

En otra terminal, inicia el frontend:

```bash
npm --prefix frontend run dev
```

Abre [DependencyGuard](http://127.0.0.1:5173/), selecciona un proyecto y pulsa **Analizar proyecto**. Usa **Administrar** para crear, editar y eliminar registros. Los cambios se guardan en AuraDB.

## Despliegue

El despliegue está preparado para GCP: backend en Cloud Run, frontend en Firebase Hosting y contraseña de Neo4j en Secret Manager. La base de datos permanece en AuraDB.

- `infra/` contiene Terraform.
- `.github/workflows/deploy.yml` publica la imagen del backend y aplica Terraform al subir cambios a `main`.
