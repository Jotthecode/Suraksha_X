from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..models import Incident
from ..pages import render_dashboard
from ..security import require_admin

router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/police_dashboard", response_class=HTMLResponse, include_in_schema=False)
def police_dashboard(request: Request, db: Session = Depends(get_db)):
    incidents = db.scalars(select(Incident).order_by(Incident.id.desc()).limit(100)).all()
    base_url = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return render_dashboard(incidents, base_url)


@router.get("/admin/incidents")
def incidents_json(db: Session = Depends(get_db)):
    rows = db.scalars(select(Incident).order_by(Incident.id.desc()).limit(200)).all()
    return {
        "incidents": [
            {
                "incident_id": r.code,
                "user_name": r.user_name,
                "trigger": r.trigger,
                "latitude": r.lat,
                "longitude": r.lon,
                "nearest_police_stations": r.nearest_stations,
                "contacts": r.contacts,
                "sms_status": r.sms_status,
                "call_status": r.call_status,
                "status": r.status,
                "tracking_session_id": r.session_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }
