import yfinance as yf
import feedparser
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

SP500_TOP = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","JPM","TSLA","V","XOM",
    "MA","JNJ","PG","HD","COST","MRK","ABBV","CVX","CRM","BAC","NFLX",
    "AMD","WMT","KO","PEP","MCD","CSCO","ABT","GE","ADBE","TXN","NKE",
    "ORCL","QCOM","MS","CAT","AMGN","GS","SYK","AXP","NOW","SNOW","CRWD",
    "PANW","NET","DDOG","ZS","FTNT","MCHP","KLAC","LRCX","AMAT","SNPS",
    "CDNS","NXPI","INTU","SPGI","MCO","BLK","CB","AON","MMC","ITW","EMR",
    "ETN","NOC","RTX","HON","UNP","NSC","FDX","UPS","DE","PLD","AMT",
    "EQIX","DLR","PSA","EW","ISRG","VRTX","REGN","GILD","BMY","LLY"
]

EUROPA = [
    "ASML.AS","SAP.DE","AZN.L","SHEL.L","BP.L",
    "SAN.MC","IBE.MC","ITX.MC","ENEL.MI","ENI.MI"
]

CRIPTO = [
    "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD",
    "ADA-USD","DOGE-USD","AVAX-USD","LINK-USD","DOT-USD"
]

MATERIAS_PRIMAS = [
    "GLD","SLV","USO","UNG","CORN","WEAT","CPER","PALL"
]

ETFS = [
    "SPY","QQQ","IWM","VTI","VOO","VEA","VWO","AGG",
    "TLT","HYG","GDX","XLF","XLK","XLE","XLV","ARKK","SOXX"
]

TODOS_LOS_TICKERS = list(set(SP500_TOP + EUROPA + CRIPTO + MATERIAS_PRIMAS + ETFS))


def calcular_rsi(serie, periodos=14):
    delta = serie.diff()
    ganancia = delta.clip(lower=0).rolling(periodos).mean()
    perdida  = (-delta.clip(upper=0)).rolling(periodos).mean()
    rs = ganancia / perdida
    return 100 - (100 / (1 + rs))


def _fetch_ticker(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="60d")
        if hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        vol   = hist["Volume"]

        precio_hoy  = close.iloc[-1]
        precio_ayer = close.iloc[-2]
        precio_5d   = close.iloc[-5] if len(close) >= 5 else close.iloc[0]
        volumen_hoy = vol.iloc[-1]
        volumen_avg = vol.mean()

        cambio_1d = (precio_hoy / precio_ayer - 1) * 100
        cambio_5d = (precio_hoy / precio_5d   - 1) * 100
        spike_vol = volumen_hoy / volumen_avg if volumen_avg > 0 else 1

        # Medias moviles
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20

        # RSI
        rsi = calcular_rsi(close).iloc[-1]

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd  = ema12 - ema26
        senal = macd.ewm(span=9).mean()
        macd_val  = round(macd.iloc[-1], 4)
        senal_val = round(senal.iloc[-1], 4)
        macd_cruce = "ALCISTA" if macd_val > senal_val else "BAJISTA"

        # Tendencia precio vs medias
        tendencia = "ALCISTA" if precio_hoy > ma20 > ma50 else (
                    "BAJISTA" if precio_hoy < ma20 < ma50 else "LATERAL")

        return {
            "ticker":      ticker,
            "precio":      round(precio_hoy, 4),
            "cambio_1d":   round(cambio_1d, 2),
            "cambio_5d":   round(cambio_5d, 2),
            "spike_vol":   round(spike_vol, 2),
            "rsi":         round(rsi, 1),
            "macd_cruce":  macd_cruce,
            "tendencia":   tendencia,
            "sobre_ma20":  precio_hoy > ma20,
        }
    except Exception:
        return None


def obtener_precios(max_workers=20):
    print(f"Descargando {len(TODOS_LOS_TICKERS)} activos...")
    resultados = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {executor.submit(_fetch_ticker, t): t for t in TODOS_LOS_TICKERS}
        for futuro in as_completed(futuros):
            dato = futuro.result()
            if dato:
                resultados.append(dato)
    print(f"  {len(resultados)} activos descargados")
    return resultados


def filtrar_interesantes(datos: list, top_n=30) -> list:
    for d in datos:
        # Bonus si RSI indica sobreventa (oportunidad de compra)
        rsi_bonus = max(0, (40 - d["rsi"]) / 10) if d["rsi"] < 40 else 0
        # Bonus si MACD alcista
        macd_bonus = 1.5 if d["macd_cruce"] == "ALCISTA" else 0

        score = (
            abs(d["cambio_1d"]) * 1.5 +
            abs(d["cambio_5d"]) * 0.8 +
            (d["spike_vol"] - 1) * 2.0 +
            rsi_bonus +
            macd_bonus
        )
        d["score"] = round(score, 2)

    return sorted(datos, key=lambda x: x["score"], reverse=True)[:top_n]


def obtener_noticias() -> list:
    feeds = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    ]
    titulares = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            titulares += [e.title for e in feed.entries[:10]]
        except Exception:
            continue
    print(f"  {len(titulares)} noticias obtenidas")
    return titulares[:25]


def obtener_insider_trading() -> list:
    urls = [
        ("CEO/CFO", "http://openinsider.com/latest-ceo-cfo-purchases-25k"),
        ("Cluster",  "http://openinsider.com/latest-cluster-buys"),
    ]
    operaciones = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for tipo, url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            tabla = soup.find("table", {"class": "tinytable"})
            if not tabla:
                continue
            for fila in tabla.find_all("tr")[1:11]:
                celdas = fila.find_all("td")
                if len(celdas) < 12:
                    continue
                try:
                    operaciones.append({
                        "tipo":    tipo,
                        "ticker":  celdas[3].text.strip(),
                        "empresa": celdas[4].text.strip()[:40],
                        "cargo":   celdas[6].text.strip(),
                        "precio":  celdas[8].text.strip(),
                        "valor":   celdas[12].text.strip(),
                        "fecha":   celdas[2].text.strip()[:10],
                    })
                except Exception:
                    continue
        except Exception:
            continue
    print(f"  {len(operaciones)} operaciones insider obtenidas")
    return operaciones


def obtener_fear_greed() -> dict:
    try:
        resp = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        data = resp.json()
        valor = data["fear_and_greed"]["score"]
        rating = data["fear_and_greed"]["rating"]
        return {"valor": round(valor, 1), "rating": rating}
    except Exception:
        return {"valor": 50, "rating": "neutral"}


def obtener_proximos_resultados() -> list:
    tickers_importantes = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","JPM","BAC","GS"]
    proximos = []
    for ticker in tickers_importantes:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None and not cal.empty:
                fecha = str(cal.columns[0].date()) if hasattr(cal.columns[0], 'date') else str(cal.columns[0])
                proximos.append({"ticker": ticker, "fecha_resultados": fecha})
        except Exception:
            continue
    print(f"  {len(proximos)} fechas de resultados obtenidas")
    return proximos


def obtener_datos_macro() -> dict:
    macro = {}
    try:
        spy  = yf.Ticker("SPY").history(period="5d")["Close"]
        vix  = yf.Ticker("^VIX").history(period="5d")["Close"]
        gold = yf.Ticker("GLD").history(period="5d")["Close"]
        usd  = yf.Ticker("DX-Y.NYB").history(period="5d")["Close"]

        macro["SPY_cambio_5d"]  = round((spy.iloc[-1]  / spy.iloc[0]  - 1) * 100, 2)
        macro["VIX_actual"]     = round(vix.iloc[-1], 2)
        macro["VIX_tendencia"]  = "SUBIENDO" if vix.iloc[-1] > vix.iloc[0] else "BAJANDO"
        macro["GOLD_cambio_5d"] = round((gold.iloc[-1] / gold.iloc[0] - 1) * 100, 2)
        macro["USD_cambio_5d"]  = round((usd.iloc[-1]  / usd.iloc[0]  - 1) * 100, 2)
    except Exception:
        pass
    print(f"  Datos macro obtenidos")
    return macro
def obtener_noticias_por_ticker(tickers: list) -> dict:
    """Busca noticias especificas para cada ticker del top 10"""
    noticias_ticker = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for ticker in tickers[:10]:
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)
            titulares = [e.title for e in feed.entries[:5]]
            if titulares:
                noticias_ticker[ticker] = titulares
        except Exception:
            continue
    
    print(f"  Noticias especificas obtenidas para {len(noticias_ticker)} tickers")
    return noticias_ticker

def obtener_datos_completos():
    todos    = obtener_precios()
    top30    = filtrar_interesantes(todos, top_n=30)
    noticias = obtener_noticias()
    insiders = obtener_insider_trading()
    fear     = obtener_fear_greed()
    macro    = obtener_datos_macro()
    earnings = obtener_proximos_resultados()
    
    # Noticias especificas de los top tickers
    top_tickers = [d["ticker"] for d in top30[:10]]
    noticias_especificas = obtener_noticias_por_ticker(top_tickers)
    
    return top30, noticias, insiders, fear, macro, earnings, noticias_especificas