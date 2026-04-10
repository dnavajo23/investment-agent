import json
import os
import yfinance as yf
from datetime import date, timedelta

ARCHIVO = "historial_recomendaciones.json"

def guardar_recomendaciones(recomendaciones: list):
    """Guarda las recomendaciones de hoy en el historial"""
    historial = cargar_historial()
    
    entrada = {
        "fecha": str(date.today()),
        "recomendaciones": recomendaciones,
        "verificado": False
    }
    
    historial.append(entrada)
    
    with open(ARCHIVO, "w") as f:
        json.dump(historial, f, indent=2)
    
    print(f"  {len(recomendaciones)} recomendaciones guardadas en historial")


def cargar_historial() -> list:
    if not os.path.exists(ARCHIVO):
        return []
    with open(ARCHIVO, "r") as f:
        return json.load(f)


def verificar_aciertos() -> str:
    """Comprueba recomendaciones de hace 7 dias y calcula aciertos"""
    historial = cargar_historial()
    fecha_objetivo = str(date.today() - timedelta(days=7))
    
    entradas_pendientes = [
        e for e in historial 
        if e["fecha"] == fecha_objetivo and not e["verificado"]
    ]
    
    if not entradas_pendientes:
        return ""
    
    resumen = "\n=== RESULTADO DE RECOMENDACIONES DE HACE 7 DIAS ===\n"
    aciertos = 0
    total = 0
    
    for entrada in entradas_pendientes:
        for rec in entrada["recomendaciones"]:
            ticker  = rec.get("ticker")
            accion  = rec.get("accion")
            precio_entrada = rec.get("precio")
            
            if not ticker or not precio_entrada:
                continue
            
            try:
                hist = yf.Ticker(ticker).history(period="8d")["Close"]
                if hist.empty:
                    continue
                
                precio_actual = hist.iloc[-1]
                cambio = (precio_actual / precio_entrada - 1) * 100
                
                # Acierto si recomendamos COMPRAR y subio, o EVITAR y bajo
                acierto = (accion == "COMPRAR" and cambio > 0) or \
                          (accion == "EVITAR"  and cambio < 0)
                
                if acierto:
                    aciertos += 1
                total += 1
                
                emoji = "OK" if acierto else "FALLO"
                resumen += f"{emoji} {ticker}: {accion} a ${precio_entrada:.2f} -> ahora ${precio_actual:.2f} ({cambio:+.1f}%)\n"
            
            except Exception:
                continue
        
        # Marcar como verificado
        entrada["verificado"] = True
    
    # Guardar historial actualizado
    with open(ARCHIVO, "w") as f:
        json.dump(historial, f, indent=2)
    
    if total > 0:
        tasa = (aciertos / total) * 100
        resumen += f"\nTASA DE ACIERTO: {aciertos}/{total} ({tasa:.0f}%)\n"
        resumen += "=" * 45 + "\n"
    
    return resumen


def extraer_recomendaciones_del_reporte(reporte: str, top30: list) -> list:
    """Extrae los tickers recomendados del reporte para guardarlos"""
    recomendaciones = []
    precios = {d["ticker"]: d["precio"] for d in top30}
    
    for linea in reporte.split("\n"):
        for ticker, precio in precios.items():
            if ticker in linea:
                if "COMPRAR" in linea.upper():
                    recomendaciones.append({
                        "ticker": ticker,
                        "accion": "COMPRAR",
                        "precio": precio
                    })
                elif "EVITAR" in linea.upper():
                    recomendaciones.append({
                        "ticker": ticker,
                        "accion": "EVITAR",
                        "precio": precio
                    })
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for r in recomendaciones:
        if r["ticker"] not in vistos:
            vistos.add(r["ticker"])
            unicos.append(r)
    
    return unicos