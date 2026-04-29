import requests
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

def enviar_telegram(reporte: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Dividir en trozos de 4000 caracteres (limite de Telegram)
    trozos = [reporte[i:i+4000] for i in range(0, len(reporte), 4000)]
    
    for i, trozo in enumerate(trozos):
        if len(trozos) > 1:
            prefijo = f"[{i+1}/{len(trozos)}]\n"
        else:
            prefijo = ""
        
        requests.post(url, data={
            "chat_id": chat_id,
            "text": prefijo + trozo,
            "parse_mode": "Markdown"
        })
    
    print(f"Reporte enviado por Telegram ({len(trozos)} mensajes)")
