"""Permite cambios solo con una sesión de Google del propietario."""

import os

from fastapi import HTTPException, Request
from firebase_admin import auth, initialize_app

editor_email = os.getenv("EDITOR_EMAIL", "").strip()
project_id = os.getenv("FIREBASE_PROJECT_ID", "")
firebase_app = initialize_app(options={"projectId": project_id}) if project_id else None


# Revisar la sesión antes de cualquier operación de escritura
def require_editor(request: Request):
    # Permitir consultas sin iniciar sesión
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    verify_editor(request)


# Comprobar la identidad y el correo autorizado por el servidor
def verify_editor(request: Request):
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")

    # Pedir un token antes de revisar los permisos
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            401, "Inicia sesión para modificar los datos.", headers={"WWW-Authenticate": "Bearer"}
        )

    # Impedir cambios si falta la configuración del servidor
    if firebase_app is None or not editor_email:
        raise HTTPException(503, "El inicio de sesión no está disponible.")

    # Verificar la firma, el proyecto, el emisor y la vigencia del token
    try:
        claims = auth.verify_id_token(token, app=firebase_app)
    except auth.CertificateFetchError:
        # Avisar si no se pudieron consultar los certificados de Google
        raise HTTPException(503, "No se pudo verificar la sesión. Intenta de nuevo.")
    except (auth.InvalidIdTokenError, ValueError):
        # Rechazar tokens inválidos o vencidos
        raise HTTPException(
            401, "Tu sesión no es válida. Inicia sesión de nuevo.", headers={"WWW-Authenticate": "Bearer"}
        )

    # Aceptar únicamente el correo verificado mediante Google
    if (
        claims.get("email") != editor_email
        or claims.get("email_verified") is not True
        or claims.get("firebase", {}).get("sign_in_provider") != "google.com"
    ):
        raise HTTPException(403, "Esta cuenta no tiene permiso para modificar los datos.")
