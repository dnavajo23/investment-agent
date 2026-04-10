import schedule
import time
from main import ejecutar_agente

def trabajo():
    print("Ejecutando agente de inversiones...")
    try:
        ejecutar_agente()
    except Exception as e:
        print(f"Error en la ejecucion: {e}")

# Programar para las 8:50 todos los dias de lunes a viernes
schedule.every().monday.at("08:50").do(trabajo)
schedule.every().tuesday.at("08:50").do(trabajo)
schedule.every().wednesday.at("08:50").do(trabajo)
schedule.every().thursday.at("08:50").do(trabajo)
schedule.every().friday.at("08:50").do(trabajo)

print("Scheduler iniciado. Esperando las 8:50...")
print("Mantén esta ventana abierta para que funcione.")

while True:
    schedule.run_pending()
    time.sleep(30)