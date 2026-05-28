import json
import os
import base64
import requests
from datetime import date
from historial import cargar_historial

GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
GITHUB_REPO   = os.getenv("GITHUB_REPO")   # formato: "usuario/repo"
ARCHIVO_JSON  = "datos_dashboard.json"


def construir_payload() -> dict:
    """
    Lee el historial de recomendaciones y construye el JSON que consume el dashboard.
    Solo incluye posiciones de COMPRAR. Los precios actuales los obtendrá el dashboard
    en el navegador vía la API pública de Yahoo Finance.
    """
    historial = cargar_historial()

    posiciones = {}
    for entrada in historial:
        for rec in entrada.get("recomendaciones", []):
            if rec.get("accion") != "COMPRAR":
                continue
            ticker = rec.get("ticker")
            if not ticker or ticker in posiciones:
                continue
            posiciones[ticker] = {
                "ticker":      ticker,
                "fecha":       entrada["fecha"],
                "precio":      rec.get("precio"),
                "take_profit": rec.get("take_profit"),
                "stop_loss":   rec.get("stop_loss"),
            }

    return {
        "actualizado": str(date.today()),
        "posiciones":  list(posiciones.values()),
    }


def publicar_en_github(payload: dict):
    """
    Hace upsert del archivo datos_dashboard.json en la rama main del repo
    usando la API REST de GitHub. No necesita git instalado.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("  GITHUB_TOKEN o GITHUB_REPO no configurados, saltando publicacion")
        return

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARCHIVO_JSON}"

    contenido_b64 = base64.b64encode(
        json.dumps(payload, indent=2, ensure_ascii=False).encode()
    ).decode()

    # Obtener SHA actual si el archivo ya existe (necesario para actualizarlo)
    sha = None
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    body = {
        "message": f"dashboard: actualizar datos {payload['actualizado']}",
        "content": contenido_b64,
    }
    if sha:
        body["sha"] = sha

    resp = requests.put(url, headers=headers, json=body, timeout=15)
    if resp.status_code in (200, 201):
        print(f"  Dashboard publicado en GitHub ({len(payload['posiciones'])} posiciones)")
    else:
        print(f"  Error al publicar dashboard: {resp.status_code} {resp.text[:200]}")


def actualizar_dashboard():
    print("Actualizando dashboard...")
    payload = construir_payload()
    publicar_en_github(payload)
