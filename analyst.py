import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

def analizar(top_activos, noticias, insiders, fear_greed, macro, earnings, noticias_especificas) -> str:

    noticias_fmt = ""
    for ticker, titulares in noticias_especificas.items():
        noticias_fmt += f"\n{ticker}:\n"
        for t in titulares:
            noticias_fmt += f"  - {t}\n"

    prompt = f"""
Eres un analista financiero experto. Genera un reporte diario claro, util y bien estructurado.

=== DATOS DISPONIBLES ===

FEAR & GREED: {fear_greed['valor']}/100 - {fear_greed['rating']}
VIX: {macro.get('VIX_actual', 'N/A')} ({macro.get('VIX_tendencia', 'N/A')})
SPY 5 dias: {macro.get('SPY_cambio_5d', 'N/A')}%
ORO 5 dias: {macro.get('GOLD_cambio_5d', 'N/A')}%
DOLAR 5 dias: {macro.get('USD_cambio_5d', 'N/A')}%

PROXIMOS RESULTADOS TRIMESTRALES:
{earnings}

ACTIVOS MAS ACTIVOS HOY:
{top_activos}

NOTICIAS POR TICKER:
{noticias_fmt}

COMPRAS DE INSIDERS (openinsider.com):
{insiders}

NOTICIAS GENERALES:
{chr(10).join(noticias)}

=== INSTRUCCIONES ===

Puntua cada activo del 1 al 10 sumando estos factores:
- Insider CEO/CFO comprando mas de 100k: +3 puntos (es la senal mas importante)
- Insider otro directivo comprando: +2 puntos
- RSI entre 30-45 (sobreventa moderada): +2 puntos
- MACD alcista: +1 punto
- Noticias positivas especificas del ticker: +2 puntos
- Tendencia alcista (sobre MA20 y MA50): +1 punto
- Volumen inusual con precio subiendo: +1 punto
- RSI mayor de 70: -3 puntos
- Noticias negativas: -2 puntos
- Resultados trimestrales en menos de 5 dias: -2 puntos

Solo incluye acciones con puntuacion de 6 o mas.
Si ninguna llega a 6, escribe: HOY NO HAY OPORTUNIDADES CLARAS.

Para calcular entrada, take profit y stop loss usa estos criterios:
- Entrada: precio actual o ligeramente por debajo si hay soporte tecnico
- Take Profit: entre 8% y 20% segun el horizonte (dias=8%, semanas=12%, meses=20%)
- Stop Loss: siempre entre 4% y 7% por debajo de la entrada para limitar perdidas
- Redondea los precios a 2 decimales

=== FORMATO DEL REPORTE ===

Escribe el reporte exactamente asi, sin cambiar la estructura:

REPORTE DE INVERSION
Fecha: [fecha de hoy]

RESUMEN DEL MERCADO
Miedo/Codicia: [valor] - [que significa hoy]
Volatilidad: [VIX y lo que implica]
Tendencia general: [frase sobre SPY, oro y dolar]
Conclusion: [es buen momento para invertir? si/no y por que en una frase]

---------------

TOP 5 DEL DIA

#1 [TICKER] - [NOMBRE EMPRESA] - [X/10]
Precio actual: $[precio]
Accion: COMPRAR / ESPERAR / EVITAR
Riesgo: bajo / medio / alto
Horizonte: dias / semanas / meses
Entrada: $[precio de entrada recomendado]
Take Profit: $[objetivo] ([X]% de ganancia)
Stop Loss: $[limite] ([X]% de perdida maxima)
Por que:
- [motivo 1, menciona si hay insider y el cargo y cuanto compro]
- [motivo 2 tecnico]
- [motivo 3 noticia si existe]

#2 [TICKER] - [NOMBRE EMPRESA] - [X/10]
Precio actual: $[precio]
Accion: COMPRAR / ESPERAR / EVITAR
Riesgo: bajo / medio / alto
Horizonte: dias / semanas / meses
Entrada: $[precio de entrada recomendado]
Take Profit: $[objetivo] ([X]% de ganancia)
Stop Loss: $[limite] ([X]% de perdida maxima)
Por que:
- [motivo 1]
- [motivo 2]
- [motivo 3 si existe]

#3 [TICKER] - [NOMBRE EMPRESA] - [X/10]
Precio actual: $[precio]
Accion: COMPRAR / ESPERAR / EVITAR
Riesgo: bajo / medio / alto
Horizonte: dias / semanas / meses
Entrada: $[precio de entrada recomendado]
Take Profit: $[objetivo] ([X]% de ganancia)
Stop Loss: $[limite] ([X]% de perdida maxima)
Por que:
- [motivo 1]
- [motivo 2]
- [motivo 3 si existe]

#4 [TICKER] - [NOMBRE EMPRESA] - [X/10]
Precio actual: $[precio]
Accion: COMPRAR / ESPERAR / EVITAR
Riesgo: bajo / medio / alto
Horizonte: dias / semanas / meses
Entrada: $[precio de entrada recomendado]
Take Profit: $[objetivo] ([X]% de ganancia)
Stop Loss: $[limite] ([X]% de perdida maxima)
Por que:
- [motivo 1]
- [motivo 2]
- [motivo 3 si existe]

#5 [TICKER] - [NOMBRE EMPRESA] - [X/10]
Precio actual: $[precio]
Accion: COMPRAR / ESPERAR / EVITAR
Riesgo: bajo / medio / alto
Horizonte: dias / semanas / meses
Entrada: $[precio de entrada recomendado]
Take Profit: $[objetivo] ([X]% de ganancia)
Stop Loss: $[limite] ([X]% de perdida maxima)
Por que:
- [motivo 1]
- [motivo 2]
- [motivo 3 si existe]

---------------

AVISO DEL DIA
[Un riesgo importante a tener en cuenta hoy en una o dos frases]

(*) Analisis informativo, no consejo financiero.

=== REGLAS IMPORTANTES ===
- Si un insider ha comprado, siempre mencionalo como primer motivo con su cargo y cantidad
- Solo usa datos reales de los proporcionados arriba, no inventes nada
- El reporte debe ser conciso y caber en pocos mensajes de WhatsApp
- Escribe en español, de forma directa y sin lenguaje vago
- Solo incluye oportunidades con puntuacion 6 o mas
- Si ninguna supera 6 escribe: HOY NO HAY OPORTUNIDADES CLARAS DE INVERSION
"""

    mensaje = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    return mensaje.content[0].text