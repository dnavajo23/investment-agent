import json
import os
import base64
import requests
import yfinance as yf
from datetime import date
from historial import cargar_historial

GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
GITHUB_REPO   = os.getenv("GITHUB_REPO")
ARCHIVO_JSON  = "datos_dashboard.json"


def obtener_precio_actual(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if hist.empty:
            return {}
        precio_actual = round(hist["Close"].iloc[-1], 2)
        precio_prev   = round(hist["Close"].iloc[-2], 2) if len(hist) >= 2 else precio_actual
        cambio_1d     = round((precio_actual / precio_prev - 1) * 100, 2)
        return {"precio_actual": precio_actual, "cambio_1d": cambio_1d}
    except Exception:
        return {}


def construir_payload() -> dict:
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

    # Enriquecer con precio actual desde yfinance
    print(f"  Obteniendo precios actuales para {len(posiciones)} posiciones...")
    for ticker, datos in posiciones.items():
        precio_info = obtener_precio_actual(ticker)
        datos.update(precio_info)

    return {
        "actualizado": str(date.today()),
        "posiciones":  list(posiciones.values()),
    }


def publicar_en_github(payload: dict):
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
        print(f"  Dashboard publicado ({len(payload['posiciones'])} posiciones con precios actuales)")
    else:
        print(f"  Error al publicar dashboard: {resp.status_code} {resp.text[:200]}")


def actualizar_dashboard():
    print("Actualizando dashboard...")
    payload = construir_payload()
    publicar_en_github(payload)
