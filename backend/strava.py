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
 
def fetch_athlete_stats(access_token: str, athlete_id: str) -> dict:
    """Fetch all-time athlete stats from Strava (1 request, no pagination)"""
    url = f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    data = res.json()

    def extract(totals):
        return {
            "count": totals.get("count", 0),
            "distance_km": round(totals.get("distance", 0) / 1000, 1),
            "moving_time_h": round(totals.get("moving_time", 0) / 3600, 1),
            "elevation_m": round(totals.get("elevation_gain", 0), 0),
        }

    return {
        "runs": extract(data.get("all_run_totals", {})),
        "rides": extract(data.get("all_ride_totals", {})),
        "swims": extract(data.get("all_swim_totals", {})),
    }

def fetch_activity_detail(access_token: str, activity_id: int) -> dict:
    """Fetch full activity detail from Strava API"""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    return res.json()

def fetch_activity_streams(access_token: str, activity_id: int) -> dict:
    """Fetch HR, distance, time, altitude streams for an activity"""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers, params={
        "keys": "heartrate,distance,time,altitude,latlng",
        "key_type": "time"
    }, timeout=15)
    res.raise_for_status()
    streams = {}
    for s in res.json():
        streams[s["type"]] = s["data"]
    return streams

def fetch_activity_laps(access_token: str, activity_id: int) -> list:
    """Fetch laps/splits for an activity"""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/laps"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    return res.json()

def procesar_detalle(detail: dict, streams: dict, laps: list, fc_max: int) -> dict:
    """Process all activity data into a structured response"""
    fc = int(detail.get("average_heartrate") or 0)
    max_fc = int(detail.get("max_heartrate") or 0)
    activity_type = detail.get("type", "Run")

    # Process laps/splits
    splits = []
    for lap in laps:
        lap_fc = int(lap.get("average_heartrate") or 0)
        splits.append({
            "distance_km": round(lap.get("distance", 0) / 1000, 2),
            "elapsed_time": lap.get("elapsed_time", 0),
            "moving_time": lap.get("moving_time", 0),
            "pace": formatear_ritmo(lap.get("average_speed", 0), activity_type),
            "fc": lap_fc,
            "zona": clasificar_zona(lap_fc, fc_max),
            "elevation_gain": round(lap.get("total_elevation_gain", 0), 1),
        })

    # Downsample HR stream for chart (max ~200 points)
    hr_chart = []
    hr_data = streams.get("heartrate", [])
    time_data = streams.get("time", [])
    if hr_data and time_data:
        step = max(1, len(hr_data) // 200)
        for i in range(0, len(hr_data), step):
            hr_chart.append({
                "time_sec": time_data[i],
                "hr": hr_data[i],
                "zona": clasificar_zona(hr_data[i], fc_max),
            })

    # Downsample altitude stream
    alt_chart = []
    alt_data = streams.get("altitude", [])
    dist_data = streams.get("distance", [])
    if alt_data and dist_data:
        step = max(1, len(alt_data) // 200)
        for i in range(0, len(alt_data), step):
            alt_chart.append({
                "distance_km": round(dist_data[i] / 1000, 2),
                "altitude": round(alt_data[i], 1),
            })

    # Route coordinates
    route = []
    latlng_data = streams.get("latlng", [])
    if latlng_data:
        step = max(1, len(latlng_data) // 300)
        for i in range(0, len(latlng_data), step):
            route.append(latlng_data[i])

    # Calculate load (TRIMP)
    fc_pct = round(fc / fc_max * 100, 1) if fc > 0 else 0
    duration_min = round(detail.get("moving_time", 0) / 60, 1)
    if fc_pct > 0:
        load = round(duration_min * (fc_pct / 100) ** 1.92)
    else:
        base = {"Run": 0.8, "Ride": 0.5, "Swim": 0.9, "WeightTraining": 0.4}.get(activity_type, 0.3)
        load = round(duration_min * base)

    result = {
        "id": detail["id"],
        "name": detail.get("name", ""),
        "type": activity_type,
        "date": detail.get("start_date_local", "")[:10],
        "start_time": detail.get("start_date_local", "")[11:16],
        "distance_km": round(detail.get("distance", 0) / 1000, 2),
        "pace": formatear_ritmo(detail.get("average_speed", 0), activity_type),
        "max_speed_pace": formatear_ritmo(detail.get("max_speed", 0), activity_type),
        "fc": fc,
        "fc_max": max_fc,
        "fc_pct": fc_pct,
        "zona": clasificar_zona(fc, fc_max),
        "duration_min": duration_min,
        "elapsed_min": round(detail.get("elapsed_time", 0) / 60, 1),
        "elevation_gain": round(detail.get("total_elevation_gain", 0), 1),
        "calories": detail.get("calories", 0),
        "load": load,
        "splits": splits,
        "hr_chart": hr_chart,
        "alt_chart": alt_chart,
        "route": route,
        "description": detail.get("description", ""),
    }

    # Cycling-specific
    if activity_type == "Ride":
        result["avg_speed_kmh"] = round(detail.get("average_speed", 0) * 3.6, 1)
        result["max_speed_kmh"] = round(detail.get("max_speed", 0) * 3.6, 1)
        result["avg_watts"] = detail.get("average_watts", 0)
        result["max_watts"] = detail.get("max_watts", 0)
        result["weighted_avg_watts"] = detail.get("weighted_average_watts", 0)
        result["kilojoules"] = detail.get("kilojoules", 0)

    # Swim-specific
    if activity_type == "Swim":
        dist_m = detail.get("distance", 0)
        moving_sec = detail.get("moving_time", 0)
        if dist_m > 0 and moving_sec > 0:
            pace_100m_sec = (moving_sec / dist_m) * 100
            m = int(pace_100m_sec // 60)
            s = int(pace_100m_sec % 60)
            result["pace_100m"] = f"{m}:{s:02d} /100m"
        else:
            result["pace_100m"] = "—"
        result["pool_length"] = detail.get("pool_length", 0)
        result["avg_strokes"] = detail.get("average_cadence", 0)
        result["total_strokes"] = int(detail.get("average_cadence", 0) * moving_sec / 60) if detail.get("average_cadence") else 0

    return result


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