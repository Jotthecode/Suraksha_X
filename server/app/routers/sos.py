"""SOS dispatch and live location sharing."""

import datetime as dt
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..models import Incident, LocationPoint, TrackingSession, User, utcnow
from ..pages import render_tracking_page
from ..security import current_user
from ..services.notify import send_sos
from ..services.risk import get_crime_predictor

router = APIRouter(tags=["sos"])

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
MAX_TRAIL_POINTS = 500


class Contact(BaseModel):
    name: str = ""
    phone: str = ""
    relation: str = "Guardian"


class DispatchIn(BaseModel):
    latitude: float
    longitude: float
    session_id: str | None = None
    user_name: str | None = None
    trigger_reason: str = "SOS"
    contacts: list[Contact] | None = None


class TrackingIn(BaseModel):
    session_id: str
    latitude: float
    longitude: float
    accuracy: float | None = None
    speed: float | None = None
    battery: str | None = None
    user_name: str | None = None


def _base_url(request: Request) -> str:
    return config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")


def _aware(value: dt.datetime | None):
    # SQLite returns naive datetimes; treat them as UTC
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


def _is_live(session: TrackingSession) -> bool:
    return session.is_active and _aware(session.expires_at) > utcnow()


def _owned_session(db: Session, user: User, session_id: str, name: str, emergency: bool) -> TrackingSession:
    if not SESSION_ID_RE.match(session_id or ""):
        raise HTTPException(422, "Invalid session_id")
    session = db.get(TrackingSession, session_id)
    if session is None:
        session = TrackingSession(
            id=session_id,
            user_id=user.id,
            user_name=name or user.name,
            expires_at=utcnow() + dt.timedelta(hours=config.TRACKING_TTL_HOURS),
            is_active=True,  # column defaults only apply on flush, and _is_live() runs before that
            is_emergency=emergency,
        )
        db.add(session)
    elif session.user_id != user.id:
        raise HTTPException(403, "This tracking session belongs to another account")
    elif emergency:
        session.is_emergency = True
    return session


def _record_point(db: Session, session: TrackingSession, lat, lon, accuracy=None, speed=None, battery=None):
    now = utcnow()
    session.last_lat, session.last_lon = lat, lon
    session.last_accuracy, session.last_speed, session.last_battery = accuracy, speed, battery
    session.last_update = now
    db.add(LocationPoint(session_id=session.id, lat=lat, lon=lon, recorded_at=now))


@router.post("/emergency_dispatch")
def emergency_dispatch(
    body: DispatchIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    name = (body.user_name or user.name or "SurakshaX user").strip()
    session_id = body.session_id or uuid.uuid4().hex
    session = _owned_session(db, user, session_id, name, emergency=True)
    _record_point(db, session, body.latitude, body.longitude)
    tracking_url = f"{_base_url(request)}/track/{session.id}"

    contacts = [c.model_dump() for c in (body.contacts or []) if c.phone.strip()]
    if not contacts:
        contacts = [g.to_dict() for g in user.guardians]

    stations = get_crime_predictor().nearest_police(body.latitude, body.longitude, top_k=2)

    window_start = utcnow() - dt.timedelta(minutes=config.SOS_WINDOW_MINUTES)
    recent = db.scalar(
        select(func.count(Incident.id)).where(Incident.user_id == user.id, Incident.created_at >= window_start)
    )
    if recent >= config.SOS_MAX_PER_WINDOW:
        sms_status = [{"phone": c["phone"], "status": "skipped_rate_limited"} for c in contacts]
        call_status = None
    else:
        sms_status, call_status = send_sos(
            name, body.latitude, body.longitude, tracking_url, contacts, stations[0] if stations else None
        )

    incident = Incident(
        user_id=user.id,
        session_id=session.id,
        user_name=name,
        trigger=body.trigger_reason[:200],
        lat=body.latitude,
        lon=body.longitude,
        nearest_stations=stations,
        contacts=contacts,
        sms_status=sms_status,
        call_status=call_status,
    )
    db.add(incident)
    db.commit()

    return {
        "success": True,
        "incident_id": incident.code,
        "status": "DISPATCHED_ACTIVE",
        "timestamp": incident.created_at.isoformat(),
        "user_name": name,
        "trigger_source": incident.trigger,
        "coordinates": {"latitude": body.latitude, "longitude": body.longitude},
        "live_tracking_url": tracking_url,
        "tracking_session_id": session.id,
        "google_maps_url": f"https://www.google.com/maps?q={body.latitude},{body.longitude}",
        "nearest_police_stations": stations,
        "notified_contacts": contacts,
        "twilio_configured": config.TWILIO_ENABLED,
        "sms_status": sms_status,
        "call_status": call_status,
    }


@router.post("/tracking/update")
def tracking_update(body: TrackingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(db, user, body.session_id, body.user_name or "", emergency=False)
    if not _is_live(session):
        db.rollback()
        raise HTTPException(410, "Tracking session has ended")
    _record_point(db, session, body.latitude, body.longitude, body.accuracy, body.speed, body.battery)
    db.commit()
    return {"status": "updated", "session_id": session.id, "stream_interval_seconds": 5}


@router.post("/tracking/{session_id}/stop")
def tracking_stop(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.get(TrackingSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(404, "Tracking session not found")
    session.is_active = False
    db.commit()
    return {"success": True}


@router.get("/tracking/{session_id}")
def tracking_data(session_id: str, db: Session = Depends(get_db)):
    """Public, read-only: anyone holding the link (the unguessable id) can follow the location."""
    session = db.get(TrackingSession, session_id) if SESSION_ID_RE.match(session_id) else None
    if session is None:
        raise HTTPException(404, "Tracking link not found")
    trail = db.scalars(
        select(LocationPoint)
        .where(LocationPoint.session_id == session.id)
        .order_by(LocationPoint.id.desc())
        .limit(MAX_TRAIL_POINTS)
    ).all()[::-1]
    latest = None
    if session.last_lat is not None:
        latest = {
            "latitude": session.last_lat,
            "longitude": session.last_lon,
            "accuracy_meters": session.last_accuracy,
            "speed_mps": session.last_speed,
            "battery_level": session.last_battery,
            "updated_at": _aware(session.last_update).isoformat() if session.last_update else None,
        }
    return {
        "session_id": session.id,
        "user_name": session.user_name,
        "is_active": _is_live(session),
        "is_emergency": session.is_emergency,
        "created_at": _aware(session.created_at).isoformat(),
        "expires_at": _aware(session.expires_at).isoformat(),
        "latest_location": latest,
        "location_history": [{"latitude": p.lat, "longitude": p.lon} for p in trail],
    }


@router.get("/track/{session_id}", response_class=HTMLResponse, include_in_schema=False)
def tracking_page(session_id: str):
    if not SESSION_ID_RE.match(session_id):
        raise HTTPException(404, "Tracking link not found")
    return render_tracking_page(session_id)


@router.get("/api/incidents")
def my_incidents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Incident).where(Incident.user_id == user.id).order_by(Incident.id.desc()).limit(50)
    ).all()
    return {
        "incidents": [
            {
                "incident_id": r.code,
                "trigger": r.trigger,
                "latitude": r.lat,
                "longitude": r.lon,
                "status": r.status,
                "created_at": _aware(r.created_at).isoformat(),
                "tracking_session_id": r.session_id,
            }
            for r in rows
        ]
    }
