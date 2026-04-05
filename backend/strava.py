import requests
import time
import os
from datetime import datetime, timedelta
 
STRAVA_CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI  = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8000/auth/callback")
 
def get_authorization_url():
    return (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )
 
def exchange_code(code: str) -> dict:
    res = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })
    res.raise_for_status()
    return res.json()
 
def refresh_access_token(refresh_token: str) -> dict:
    res = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    })
    res.raise_for_status()
    return res.json()
 
def get_valid_token(user) -> str:
    if user.token_expires_at < int(time.time()):
        data = refresh_access_token(user.refresh_token)
        return data["access_token"], data["refresh_token"], data["expires_at"]
    return user.access_token, user.refresh_token, user.token_expires_at
 
def fetch_activities(access_token: str, days: int = 14) -> list:
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    since = int((datetime.now() - timedelta(days=days)).timestamp())
    activities = []
    page = 1
 
    while True:
        res = requests.get(url, headers=headers, params={
            "per_page": 200,
            "page": page,
            "after": since
        }, timeout=15)
        res.raise_for_status()
        data = res.json()
        if not data:
            break
        activities.extend(data)
        page += 1
        time.sleep(0.4)
 
    return activities
 
def formatear_ritmo(speed_ms: float, activity_type: str) -> str:
    if speed_ms <= 0:
        return "0"
    if activity_type == "Run":
        m = (1000 / speed_ms) / 60
        return f"{int(m)}:{int((m % 1) * 60):02d} min/km"
    return f"{round(speed_ms * 3.6, 1)} km/h"
 
def clasificar_zona(fc: int, fc_max: int) -> str:
    if fc <= 0:
        return "Sin FC"
    pct = fc / fc_max * 100
    if pct > 92:   return "Z5 - Máximo"
    if pct > 89:   return "Z4 - Umbral"
    if pct > 77:   return "Z3 - Tempo"
    if pct > 67:   return "Z2 - Aeróbico Base"
    return "Z1 - Recuperación"
 
def procesar_actividades(activities: list, fc_max: int) -> list:
    resultado = []
    for a in activities:
        fc = int(a.get("average_heartrate") or 0)
        resultado.append({
            "id": a["id"],
            "name": a["name"],
            "type": a["type"],
            "date": a["start_date_local"][:10],
            "distance_km": round(a.get("distance", 0) / 1000, 2),
            "pace": formatear_ritmo(a.get("average_speed", 0), a["type"]),
            "fc": fc,
            "fc_pct": round(fc / fc_max * 100, 1) if fc > 0 else 0,
            "zona": clasificar_zona(fc, fc_max),
            "duration_min": round(a.get("moving_time", 0) / 60, 1),
        })
    return resultado
 
def construir_prompt(activities: list, user) -> str:
    lineas = [
        f"ATLETA: FC MÁX {user.fc_max} bpm",
        "-" * 50
    ]
    for a in activities:
        if a["type"] not in ["Run", "Ride", "Swim", "WeightTraining", "Hike"]:
            continue
        emoji = {"Run": "🏃", "Ride": "🚴", "Swim": "🏊"}.get(a["type"], "🏋️")
        lineas.append(f"{emoji} {a['date']} — {a['type']}")
        lineas.append(f"   Zona: {a['zona']}")
        lineas.append(f"   Datos: {a['distance_km']}km @ {a['pace']}")
        lineas.append(f"   FC: {a['fc']} bpm ({a['fc_pct']}%)")
        lineas.append(f"   Nota: {a['name']}")
        lineas.append("-" * 40)
    return "\n".join(lineas)