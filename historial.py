import json
import os
import yfinance as yf
from datetime import date, timedelta
import re

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
                
                acierto = (accion == "COMPRAR" and cambio > 0) or \
                          (accion == "EVITAR"  and cambio < 0)
                
                if acierto:
                    aciertos += 1
                total += 1
                
                emoji = "OK" if acierto else "FALLO"
                resumen += f"{emoji} {ticker}: {accion} a ${precio_entrada:.2f} -> ahora ${precio_actual:.2f} ({cambio:+.1f}%)\n"
            
            except Exception:
                continue
        
        entrada["verificado"] = True
    
    with open(ARCHIVO, "w") as f:
        json.dump(historial, f, indent=2)
    
    if total > 0:
        tasa = (aciertos / total) * 100
        resumen += f"\nTASA DE ACIERTO: {aciertos}/{total} ({tasa:.0f}%)\n"
        resumen += "=" * 45 + "\n"
    
    return resumen


def resumen_semanal_viernes() -> str:
    """
    Solo se ejecuta los viernes. Recorre todas las recomendaciones de COMPRAR
    de los ultimos 7 dias y muestra su progreso actual vs TP y SL.
    """
    if date.today().weekday() != 4:  # 4 = viernes
        return ""

    historial = cargar_historial()
    hoy = date.today()
    hace_7 = hoy - timedelta(days=7)

    # Recoger todas las COMPRAR de la semana (sin duplicados por ticker)
    recomendaciones_semana = {}
    for entrada in historial:
        try:
            fecha_entrada = date.fromisoformat(entrada["fecha"])
        except Exception:
            continue
        if not (hace_7 <= fecha_entrada <= hoy):
            continue
        for rec in entrada["recomendaciones"]:
            if rec.get("accion") != "COMPRAR":
                continue
            ticker = rec.get("ticker")
            if not ticker or ticker in recomendaciones_semana:
                continue
            recomendaciones_semana[ticker] = {
                "fecha": entrada["fecha"],
                "precio_entrada": rec.get("precio"),
                "take_profit":    rec.get("take_profit"),
                "stop_loss":      rec.get("stop_loss"),
            }

    if not recomendaciones_semana:
        return ""

    lineas = ["\n=== SEGUIMIENTO SEMANAL DE COMPRAS ==="]
    aciertos = 0
    total = 0

    for ticker, datos in recomendaciones_semana.items():
        precio_entrada = datos["precio_entrada"]
        tp = datos.get("take_profit")
        sl = datos.get("stop_loss")

        if not precio_entrada:
            continue

        try:
            hist = yf.Ticker(ticker).history(period="8d")["Close"]
            if hist.empty:
                continue
            precio_actual = round(hist.iloc[-1], 2)
            cambio = (precio_actual / precio_entrada - 1) * 100

            # Estado respecto a TP y SL
            if tp and precio_actual >= tp:
                estado = "OBJETIVO ALCANZADO"
            elif sl and precio_actual <= sl:
                estado = "STOP LOSS TOCADO"
            elif cambio > 0:
                estado = "EN POSITIVO"
            else:
                estado = "EN NEGATIVO"

            if cambio > 0:
                aciertos += 1
            total += 1

            tp_str = f" | TP: ${tp:.2f}" if tp else ""
            sl_str = f" | SL: ${sl:.2f}" if sl else ""
            lineas.append(
                f"{ticker} [{datos['fecha']}]: entrada ${precio_entrada:.2f} -> "
                f"ahora ${precio_actual:.2f} ({cambio:+.1f}%){tp_str}{sl_str} -> {estado}"
            )

        except Exception:
            continue

    if total == 0:
        return ""

    tasa = (aciertos / total) * 100
    lineas.append(f"\nBalance semanal: {aciertos}/{total} en positivo ({tasa:.0f}%)")
    lineas.append("=" * 45)

    print(f"  Resumen semanal generado: {total} posiciones revisadas")
    return "\n".join(lineas) + "\n"


def extraer_recomendaciones_del_reporte(reporte: str, top30: list) -> list:
    """
    Extrae los tickers recomendados del reporte junto con su accion, precio,
    take profit y stop loss para poder hacer seguimiento posterior.
    """
    recomendaciones = []
    precios = {d["ticker"]: d["precio"] for d in top30}

    # Limpiar formato Markdown (asteriscos)
    reporte_limpio = re.sub(r"\*+", "", reporte)

    lineas = reporte_limpio.split("\n")

    for i, linea in enumerate(lineas):
        for ticker, precio in precios.items():
            if ticker not in linea:
                continue

            accion = None
            if "COMPRAR" in linea.upper():
                accion = "COMPRAR"
            elif "EVITAR" in linea.upper():
                accion = "EVITAR"

            if not accion:
                continue

            # Buscar TP y SL en las siguientes 15 lineas del bloque
            take_profit = None
            stop_loss = None
            for j in range(i + 1, min(i + 16, len(lineas))):
                linea_j = lineas[j]
                tp_match = re.search(r"Take Profit.*?\$([0-9]+(?:\.[0-9]+)?)", linea_j, re.IGNORECASE)
                sl_match = re.search(r"Stop Loss.*?\$([0-9]+(?:\.[0-9]+)?)", linea_j, re.IGNORECASE)
                if tp_match:
                    take_profit = float(tp_match.group(1))
                if sl_match:
                    stop_loss = float(sl_match.group(1))
                # Parar si encontramos el siguiente ticker del top
                if j > i + 1 and any(t in lineas[j] for t in precios if t != ticker):
                    break

            recomendaciones.append({
                "ticker":      ticker,
                "accion":      accion,
                "precio":      precio,
                "take_profit": take_profit,
                "stop_loss":   stop_loss,
            })
            break  # un ticker por linea es suficiente

    # Eliminar duplicados manteniendo el primero
    vistos = set()
    unicos = []
    for r in recomendaciones:
        if r["ticker"] not in vistos:
            vistos.add(r["ticker"])
            unicos.append(r)

    return unicos
