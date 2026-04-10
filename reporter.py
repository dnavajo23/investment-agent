from twilio.rest import Client
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

def enviar_whatsapp(reporte: str):
    client = Client(
        os.getenv("TWILIO_SID"),
        os.getenv("TWILIO_TOKEN")
    )
    cabecera = f"REPORTE DE INVERSION - {date.today()}\n\n"
    mensaje_completo = cabecera + reporte
    trozos = [mensaje_completo[i:i+1500] for i in range(0, len(mensaje_completo), 1500)]
    for trozo in trozos:
        client.messages.create(
            from_="whatsapp:+14155238886",
            to=f"whatsapp:+34{os.getenv('TU_TELEFONO')}",
            body=trozo
        )
    print(f"Reporte enviado por WhatsApp ({len(trozos)} mensajes)")