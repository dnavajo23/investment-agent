from fetcher import obtener_datos_completos
from analyst import analizar
from reporter import enviar_reporte
from historial import (
    guardar_recomendaciones,
    verificar_aciertos,
    extraer_recomendaciones_del_reporte
)

def ejecutar_agente():
    print("Iniciando agente de inversiones...")

    print("Verificando aciertos de la semana pasada...")
    resultado_aciertos = verificar_aciertos()

    print("Obteniendo datos de mercado...")
    top30, noticias, insiders, fear, macro, earnings, noticias_especificas = obtener_datos_completos()
    print(f"Datos listos: {len(top30)} activos | Fear&Greed: {fear['valor']} ({fear['rating']})")

    print("Analizando con IA...")
    reporte = analizar(top30, noticias, insiders, fear, macro, earnings, noticias_especificas)
    print(f"Reporte generado ({len(reporte)} caracteres)")

    if resultado_aciertos:
        reporte = resultado_aciertos + "\n" + reporte

    print("Guardando recomendaciones en historial...")
    recomendaciones = extraer_recomendaciones_del_reporte(reporte, top30)
    guardar_recomendaciones(recomendaciones)

    print("Enviando reporte...")
    enviar_reporte(reporte)
    print("Todo listo!")

if __name__ == "__main__":
    print("Arrancando...")
    ejecutar_agente()
