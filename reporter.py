import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

def enviar_telegram(reporte: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    trozos = [reporte[i:i+4000] for i in range(0, len(reporte), 4000)]
    for i, trozo in enumerate(trozos):
        prefijo = f"[{i+1}/{len(trozos)}]\n" if len(trozos) > 1 else ""
        requests.post(url, data={
            "chat_id": chat_id,
            "text": prefijo + trozo
        })
    print(f"Reporte enviado por Telegram ({len(trozos)} mensajes)")


def enviar_whatsapp(reporte: str):
    client = Client(
        os.getenv("TWILIO_SID"),
        os.getenv("TWILIO_TOKEN")
    )
    cabecera = f"REPORTE DE INVERSION - {date.today()}\n\n"
    mensaje_completo = cabecera + reporte
    trozos = [mensaje_completo[i:i+1500] for i in range(0, len(mensaje_completo), 1500)]
    for i, trozo in enumerate(trozos):
        prefijo = f"[{i+1}/{len(trozos)}]\n" if len(trozos) > 1 else ""
        try:
            client.messages.create(
                from_="whatsapp:+14155238886",
                to=f"whatsapp:+34{os.getenv('TU_TELEFONO')}",
                body=prefijo + trozo
            )
        except Exception as e:
            print(f"Error WhatsApp mensaje {i+1}: {e}")
    print(f"Reporte enviado por WhatsApp ({len(trozos)} mensajes)")


def enviar_reporte(reporte: str):
    enviar_telegram(reporte)
    enviar_whatsapp(reporte)
