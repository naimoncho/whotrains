import requests
import os
 
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
 
SYSTEM_PROMPT = (
    "Eres un entrenador de atletismo experto, especializado en pruebas de medio fondo (800m) y fondo. "
    "Analiza los datos de entrenamiento del atleta de los últimos 14 días y responde siempre en español "
    "con tres secciones claramente separadas:\n\n"
    "1. ANÁLISIS DE CARGA Y RECUPERACIÓN: evalúa la distribución de intensidades, "
    "el volumen semanal y si hay señales de fatiga o infracarga.\n\n"
    "2. PUNTOS FUERTES Y DÉBILES: qué está haciendo bien el atleta y qué necesita mejorar.\n\n"
    "3. PRÓXIMO ENTRENAMIENTO SUGERIDO: propón una sesión concreta y justifica por qué encaja con la carga actual."
)
 
def analizar(prompt_datos: str) -> str | None:
    if not ANTHROPIC_KEY:
        return None
 
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": f"Mis datos de entrenamiento:\n\n{prompt_datos}"}
                ]
            },
            timeout=30
        )
        res.raise_for_status()
        return res.json()["content"][0]["text"]
    except Exception as e:
        print(f"Error Claude API: {e}")
        return None
 