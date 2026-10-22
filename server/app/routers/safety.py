"""Area risk, safe routes, address search, nearby police and voice SOS. Public, read-only endpoints."""

import base64
import datetime as dt
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services import geo
from ..services.risk import get_crime_predictor
from ..services.routing import get_safe_route_planner
from ..services.voice import get_voice_classifier

router = APIRouter(tags=["safety"])

MAX_AUDIO_BYTES = 5 * 1024 * 1024


class Point(BaseModel):
    latitude: float
    longitude: float


class RiskIn(Point):
    lighting: float | None = None
    density: float | None = None


class RouteIn(BaseModel):
    origin: Point
    destination: Point
    alpha: float = 0.4


class PoliceIn(Point):
    count: int = 2


class SensorIn(BaseModel):
    audio_score: float = 0.0
    fall_force: float = 1.0
    heart_rate: float = 72.0
    latitude: float
    longitude: float


def _check_coords(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, "Invalid coordinates")


@router.post("/predict_risk")
def predict_risk(body: RiskIn):
    _check_coords(body.latitude, body.longitude)
    return get_crime_predictor().predict(body.latitude, body.longitude, lighting=body.lighting, density=body.density)


@router.get("/hotspots")
def hotspots(
    lat: float,
    lon: float,
    radius_km: float = Query(2.5, gt=0, le=5),
    step_km: float = Query(0.5, ge=0.25, le=2),
):
    _check_coords(lat, lon)
    cells, source = get_crime_predictor().get_grid_hotspots(lat, lon, radius_km=radius_km, step_km=step_km)
    return {
        "center": {"latitude": lat, "longitude": lon},
        "grid_resolution": f"{int(step_km * 1000)}m x {int(step_km * 1000)}m",
        "total_cells": len(cells),
        "data_source": source,
        "hotspots": cells,
    }


@router.post("/safe_route")
def safe_route(body: RouteIn):
    _check_coords(body.origin.latitude, body.origin.longitude)
    _check_coords(body.destination.latitude, body.destination.longitude)
    alpha = min(1.0, max(0.0, body.alpha))
    result = get_safe_route_planner().plan_route(
        body.origin.latitude, body.origin.longitude, body.destination.latitude, body.destination.longitude, alpha=alpha
    )
    if result.get("error"):
        return JSONResponse(result, status_code=422)
    return result


@router.get("/geocode")
def geocode(q: str = Query(..., min_length=2, max_length=200), lat: float | None = None, lon: float | None = None):
    near = (lat, lon) if lat is not None and lon is not None else None
    results = geo.geocode(q, near=near)
    if results is None:
        return JSONResponse({"error": "Address search is unavailable, try again shortly", "results": []}, status_code=503)
    return {"query": q, "results": results}


@router.get("/places/suggest")
def places_suggest(
    q: str = Query(..., min_length=1, max_length=120),
    lat: float | None = None,
    lon: float | None = None,
    limit: int = Query(8, ge=1, le=15),
):
    """Type-ahead place suggestions inside India, nearest first when lat/lon are given."""
    near = (lat, lon) if lat is not None and lon is not None else None
    results = geo.suggest_places(q, near=near, limit=limit)
    if results is None:
        return JSONResponse({"error": "Place search is unavailable, try again shortly", "results": []}, status_code=503)
    return {"query": q, "results": results}


@router.get("/places/reverse")
def places_reverse(lat: float, lon: float):
    _check_coords(lat, lon)
    result = geo.reverse_geocode(lat, lon)
    if result is None:
        return JSONResponse({"error": "Address lookup is unavailable", "label": None}, status_code=503)
    return result


@router.post("/police/nearest")
def nearest_police(body: PoliceIn):
    _check_coords(body.latitude, body.longitude)
    count = max(1, min(body.count, 20))
    stations = get_crime_predictor().nearest_police(body.latitude, body.longitude, top_k=count)
    return {
        "query_location": {"latitude": body.latitude, "longitude": body.longitude},
        "stations": stations,
        "nearest_police_stations": stations,
    }


@router.post("/analyze_status")
def analyze_status(body: SensorIn):
    """Rule-based check of sensor readings (scream score, fall force, heart rate) plus area risk."""
    _check_coords(body.latitude, body.longitude)
    risk = get_crime_predictor().predict(body.latitude, body.longitude)
    scream = body.audio_score >= 0.70
    fall = body.fall_force >= 3.0
    stress = body.heart_rate >= 120 or body.heart_rate <= 45

    if scream:
        decision, reason = "CRITICAL", "Distress sound detected"
    elif fall and stress:
        decision, reason = "CRITICAL", "Hard fall with abnormal heart rate"
    elif fall:
        decision, reason = "CRITICAL", "Hard fall detected"
    elif stress and (body.audio_score >= 0.5 or risk["category"] == "High Risk"):
        decision, reason = "CRITICAL", f"Abnormal heart rate in a {risk['category'].lower()} area"
    else:
        decision, reason = "SAFE", "Readings are normal"

    return {
        "decision": decision,
        "reason": reason,
        "location_risk": risk,
        "metrics": {"audio_score": body.audio_score, "fall_force": body.fall_force, "heart_rate": body.heart_rate},
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


@router.post("/voice_sos")
async def voice_sos(request: Request):
    """
    Distress-word detection.
    - multipart/form-data with an "audio" file  -> voice model
    - JSON {"audio_base64": "...", "audio_format": "m4a"} -> voice model
    - JSON {"phrase": "bachao"} -> keyword check on a text transcript
    """
    classifier = get_voice_classifier()
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("audio")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(422, 'Missing "audio" file')
        data = await upload.read()
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio clip too large")
        suffix = os.path.splitext(upload.filename or "")[1] or ".m4a"
        return await run_in_threadpool(classifier.classify_audio_bytes, data, suffix)

    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(422, "Expected JSON or multipart audio")

    if body.get("audio_base64"):
        data = base64.b64decode(body["audio_base64"])
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio clip too large")
        fmt = str(body.get("audio_format", "m4a")).lstrip(".")
        return await run_in_threadpool(classifier.classify_audio_bytes, data, f".{fmt}")

    return classifier.classify_audio_phrase(
        text_or_transcript=str(body.get("phrase", "")),
        audio_score=float(body.get("audio_score", 0.0)),
        noise_env=str(body.get("noise_condition", "street")),
    )
