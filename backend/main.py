from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv
import os
 
load_dotenv()
 
from database import engine, get_db
import models
import strava
import claude
import notifications
from auth import create_access_token, get_current_user
from payments import router as payments_router
 
# Crear tablas
models.Base.metadata.create_all(bind=engine)
 
app = FastAPI(title="Who Trains API", version="1.0.0")
app.include_router(payments_router)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# --- AUTH ---
 
@app.get("/auth/login")
def login():
    """Redirige al usuario a Strava para autenticarse"""
    url = strava.get_authorization_url()
    return RedirectResponse(url)
 
@app.get("/auth/callback")
def callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Strava redirige aquí con el código de autorización"""
    try:
        data = strava.exchange_code(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Error al autenticar con Strava")
 
    athlete    = data["athlete"]
    strava_id  = str(athlete["id"])
 
    user = db.query(models.User).filter(models.User.strava_id == strava_id).first()
    if not user:
        user = models.User(
            strava_id        = strava_id,
            email            = athlete.get("email", ""),
            name             = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(),
            profile_pic      = athlete.get("profile", ""),
            access_token     = data["access_token"],
            refresh_token    = data["refresh_token"],
            token_expires_at = data["expires_at"],
            is_pro           = True,
        )
        db.add(user)
    else:
        user.access_token     = data["access_token"]
        user.refresh_token    = data["refresh_token"]
        user.token_expires_at = data["expires_at"]
 
    db.commit()
    db.refresh(user)
 
    token = create_access_token({"sub": user.strava_id})
    # Redirige al frontend con el JWT
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}?token={token}")
 
# --- USUARIO ---
 
@app.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id":          current_user.id,
        "name":        current_user.name,
        "email":       current_user.email,
        "profile_pic": current_user.profile_pic,
        "is_pro":      current_user.is_pro,
        "fc_max":      current_user.fc_max,
        "ntfy_channel": current_user.ntfy_channel,
    }
 
@app.patch("/me")
def update_me(
    fc_max: int = None,
    ntfy_channel: str = None,
    weight_kg: float = None,
    height_cm: float = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if fc_max:        current_user.fc_max        = fc_max
    if ntfy_channel:  current_user.ntfy_channel  = ntfy_channel
    if weight_kg:     current_user.weight_kg     = weight_kg
    if height_cm:     current_user.height_cm     = height_cm
    db.commit()
    return {"message": "Perfil actualizado"}
 
# --- ACTIVIDADES ---
 
@app.get("/activities")
def get_activities(
    days: int = 14,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token, new_refresh, new_expires = strava.get_valid_token(current_user)
 
    # Actualizar token si fue renovado
    if token != current_user.access_token:
        current_user.access_token     = token
        current_user.refresh_token    = new_refresh
        current_user.token_expires_at = new_expires
        db.commit()
 
    try:
        raw = strava.fetch_activities(token, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener actividades: {e}")
 
    return strava.procesar_actividades(raw, current_user.fc_max)

# --- DETALLE DE ACTIVIDAD ---

@app.get("/activity/{activity_id}")
def get_activity_detail(
    activity_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token, new_refresh, new_expires = strava.get_valid_token(current_user)

    if token != current_user.access_token:
        current_user.access_token     = token
        current_user.refresh_token    = new_refresh
        current_user.token_expires_at = new_expires
        db.commit()

    try:
        detail = strava.fetch_activity_detail(token, activity_id)
        streams = strava.fetch_activity_streams(token, activity_id)
        laps = strava.fetch_activity_laps(token, activity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener actividad: {e}")

    return strava.procesar_detalle(detail, streams, laps, current_user.fc_max)

# --- ESTADÍSTICAS ---

@app.get("/stats")
def get_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token, new_refresh, new_expires = strava.get_valid_token(current_user)
 
    if token != current_user.access_token:
        current_user.access_token     = token
        current_user.refresh_token    = new_refresh
        current_user.token_expires_at = new_expires
        db.commit()
 
    # All-time stats from Strava (single API call, no pagination)
    all_time = strava.fetch_athlete_stats(token, current_user.strava_id)

    # Fetch last year activities for gym count + zone distribution
    gym_count = 0
    gym_hours = 0
    zone_distribution = {}
    try:
        raw = strava.fetch_activities(token, days=365)
        activities = strava.procesar_actividades(raw, current_user.fc_max)
        gyms = [a for a in raw if a.get("type") == "WeightTraining"]
        gym_count = len(gyms)
        gym_hours = round(sum(a.get("moving_time", 0) for a in gyms) / 3600, 1)

        # Zone distribution (all activities with distance)
        for a in activities:
            if a["distance_km"] > 0:
                zone_distribution[a["zona"]] = round(
                    zone_distribution.get(a["zona"], 0) + a["distance_km"], 1
                )
    except Exception:
        pass

    return {
        "total_runs":        all_time["runs"]["count"],
        "total_km_running":  all_time["runs"]["distance_km"],
        "total_hours_running": all_time["runs"]["moving_time_h"],
        "total_elevation_running": all_time["runs"]["elevation_m"],
        "total_rides":       all_time["rides"]["count"],
        "total_km_riding":   all_time["rides"]["distance_km"],
        "total_hours_riding": all_time["rides"]["moving_time_h"],
        "total_elevation_riding": all_time["rides"]["elevation_m"],
        "total_swims":       all_time["swims"]["count"],
        "total_km_swimming": all_time["swims"]["distance_km"],
        "total_gym":         gym_count,
        "total_hours_gym":   gym_hours,
        "zone_distribution": zone_distribution,
    }
 
# --- ANÁLISIS (solo PRO) ---
 
@app.post("/analysis")
def create_analysis(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Esta función es solo para usuarios Pro")
 
    token, new_refresh, new_expires = strava.get_valid_token(current_user)
 
    if token != current_user.access_token:
        current_user.access_token     = token
        current_user.refresh_token    = new_refresh
        current_user.token_expires_at = new_expires
        db.commit()
 
    raw        = strava.fetch_activities(token, days=14)
    activities = strava.procesar_actividades(raw, current_user.fc_max)
    prompt     = strava.construir_prompt(activities, current_user)
    analisis   = claude.analizar(prompt)
 
    if not analisis:
        raise HTTPException(status_code=500, detail="Error al generar el análisis")
 
    # Guardar en BD
    nuevo = models.Analysis(user_id=current_user.id, content=analisis)
    db.add(nuevo)
    db.commit()
 
    # Notificación móvil si tiene canal configurado
    if current_user.ntfy_channel:
        fecha = datetime.now().strftime("%Y-%m-%d")
        notifications.notificar_analisis(current_user.ntfy_channel, analisis, fecha)
 
    return {"analysis": analisis}
 
@app.get("/analysis/history")
def get_analysis_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Esta función es solo para usuarios Pro")
 
    analyses = db.query(models.Analysis)\
        .filter(models.Analysis.user_id == current_user.id)\
        .order_by(models.Analysis.created_at.desc())\
        .all()
 
    return [{"id": a.id, "content": a.content, "created_at": a.created_at} for a in analyses]
 
# --- HEALTH CHECK ---
 
@app.get("/")
def health():
    return {"status": "ok", "app": "Who Trains API"}