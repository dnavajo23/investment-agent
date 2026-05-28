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
    El formato del reporte es:
      #1 TICKER - Empresa - X/10
      ...
      Accion: COMPRAR / EVITAR
      ...
      Take Profit: $X
      Stop Loss: $X
    """
    recomendaciones = []
    precios = {d["ticker"]: d["precio"] for d in top30}

    # Limpiar formato Markdown (asteriscos, negrita, cursiva)
    reporte_limpio = re.sub(r"\*+", "", reporte)
    lineas = reporte_limpio.split("\n")

    for i, linea in enumerate(lineas):
        # Buscar linea que contenga un ticker conocido (cabecera del bloque)
        ticker_encontrado = None
        for ticker in precios:
            if ticker in linea:
                ticker_encontrado = ticker
                break

        if not ticker_encontrado:
            continue

        # Buscar accion, TP y SL en las siguientes 20 lineas del bloque
        accion = None
        take_profit = None
        stop_loss = None

        for j in range(i + 1, min(i + 21, len(lineas))):
            linea_j = lineas[j].strip()

            # Detectar accion
            if accion is None:
                if re.search(r"acci[oó]n\s*:.*comprar", linea_j, re.IGNORECASE):
                    accion = "COMPRAR"
                elif re.search(r"acci[oó]n\s*:.*evitar", linea_j, re.IGNORECASE):
                    accion = "EVITAR"
                elif re.search(r"acci[oó]n\s*:.*esperar", linea_j, re.IGNORECASE):
                    accion = "ESPERAR"

            # Detectar Take Profit
            tp_match = re.search(r"take\s*profit\s*:?\s*\$([0-9]+(?:\.[0-9]+)?)", linea_j, re.IGNORECASE)
            if tp_match:
                take_profit = float(tp_match.group(1))

            # Detectar Stop Loss
            sl_match = re.search(r"stop\s*loss\s*:?\s*\$([0-9]+(?:\.[0-9]+)?)", linea_j, re.IGNORECASE)
            if sl_match:
                stop_loss = float(sl_match.group(1))

            # Parar si llegamos al siguiente bloque (nueva entrada #N)
            if j > i + 1 and re.match(r"#\d+\s", linea_j):
                break

        # Solo guardar si encontramos una accion relevante
        if accion in ("COMPRAR", "EVITAR"):
            recomendaciones.append({
                "ticker":      ticker_encontrado,
                "accion":      accion,
                "precio":      precios[ticker_encontrado],
                "take_profit": take_profit,
                "stop_loss":   stop_loss,
            })

    # Eliminar duplicados manteniendo el primero
    vistos = set()
    unicos = []
    for r in recomendaciones:
        if r["ticker"] not in vistos:
            vistos.add(r["ticker"])
            unicos.append(r)

    return unicos
