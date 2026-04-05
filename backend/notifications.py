import requests
 
def enviar_notificacion(channel: str, titulo: str, mensaje: str):
    if not channel:
        return
 
    try:
        chunk_size = 4000
        chunks = [mensaje[i:i+chunk_size] for i in range(0, len(mensaje), chunk_size)]
        for i, chunk in enumerate(chunks):
            t = titulo if len(chunks) == 1 else f"{titulo} ({i+1}/{len(chunks)})"
            requests.post(
                f"https://ntfy.sh/{channel}",
                data=chunk.encode("utf-8"),
                headers={
                    "Title": t,
                    "Priority": "default",
                    "Tags": "running",
                    "Content-Type": "text/plain; charset=utf-8"
                },
                timeout=10
            )
    except Exception as e:
        print(f"Error ntfy: {e}")
 
def notificar_resumen(channel: str, total_km: float, fecha: str):
    enviar_notificacion(
        channel,
        f"Who Trains — {fecha}",
        f"Resumen actualizado. Has corrido {total_km:.1f}km en los últimos 14 días."
    )
 
def notificar_analisis(channel: str, analisis: str, fecha: str):
    enviar_notificacion(
        channel,
        f"Análisis semanal — {fecha}",
        analisis
    )
 