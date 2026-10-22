"""API tests. Run from server/: `python -m pytest -q` (uses a throwaway SQLite database, no network for SOS)."""

import os
import tempfile
import uuid

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ADMIN_PASSWORD"] = "admin-pass"
for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER", "PUBLIC_BASE_URL"):
    os.environ[key] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PUNE = {"latitude": 18.5204, "longitude": 73.8567}


def _signup(email, **overrides):
    data = {
        "email": email, "password": "secret123", "name": "Asha", "phone": "9876543210",
        "gender": "Female", "blood_group": "B+", "date_of_birth": "1998-04-21",
        "guardians": [{"name": "Mom", "phone": "9876500001", "relation": "Mother"}],
    }
    data.update(overrides)
    return data


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _register(client, email=None):
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/register", json=_signup(email))
    assert res.status_code == 200, res.text
    body = res.json()
    return body["token"], body["user"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["database"] == "ok"


def test_register_login_profile(client):
    token, user = _register(client, "Asha@Example.com")
    assert user["email"] == "asha@example.com"
    assert user["blood_group"] == "B+" and user["guardians"][0]["name"] == "Mom"

    dup = client.post("/api/register", json=_signup("asha@example.com"))
    assert dup.status_code == 409 and dup.json()["success"] is False

    bad = client.post("/api/login", json={"email": "asha@example.com", "password": "wrong"})
    assert bad.status_code == 401 and bad.json()["error"]

    ok = client.post("/api/login", json={"email": " ASHA@example.com ", "password": "secret123"})
    assert ok.status_code == 200 and ok.json()["token"]

    me = client.get("/api/user/profile", headers=_auth(token))
    assert me.json()["user"]["name"] == "Asha"

    assert client.get("/api/user/profile").status_code == 401
    assert client.get("/api/user/profile", headers=_auth("garbage")).status_code == 401


def test_register_validation(client):
    cases = [
        (_signup("nope"), "email"),
        (_signup("x@y.com", password="123"), "password"),
        (_signup("x@y.com", phone="12345"), "mobile"),
        (_signup("x@y.com", blood_group=""), "blood group"),
        (_signup("x@y.com", gender=""), "gender"),
        (_signup("x@y.com", guardians=[]), "emergency contact"),
        (_signup("x@y.com", guardians=[{"name": "Me", "phone": "+91 98765 43210"}]), "own number"),
        (_signup("x@y.com", guardians=[{"name": "", "phone": "9876500001"}]), "name"),
        (_signup("x@y.com", date_of_birth="21/04/1998"), "date of birth"),
    ]
    for payload, expected in cases:
        res = client.post("/api/register", json=payload)
        assert res.status_code == 400, (expected, res.text)
        assert expected in res.json()["error"].lower(), (expected, res.json())


def test_place_suggestions(client, monkeypatch):
    from app.services import geo

    calls = []

    def fake_suggest(q, near=None, limit=8):
        calls.append((q, near, limit))
        return [{"name": "Rajwada", "subtitle": "Indore, Madhya Pradesh", "lat": 22.7186, "lon": 75.8553}]

    monkeypatch.setattr(geo, "suggest_places", fake_suggest)
    res = client.get("/places/suggest", params={"q": "raj", "lat": 22.7, "lon": 75.8})
    assert res.status_code == 200 and res.json()["results"][0]["name"] == "Rajwada"
    assert calls == [("raj", (22.7, 75.8), 8)]

    monkeypatch.setattr(geo, "suggest_places", lambda *a, **k: None)
    assert client.get("/places/suggest", params={"q": "raj"}).status_code == 503

    monkeypatch.setattr(geo, "reverse_geocode", lambda lat, lon: {"label": "MG Road, Indore", "full": "x"})
    assert client.get("/places/reverse", params={"lat": 22.7, "lon": 75.8}).json()["label"] == "MG Road, Indore"


def test_guardians_round_trip(client):
    token, _ = _register(client)
    guardians = [
        {"id": "g1", "name": "Mom", "phone": "9876500001", "relation": "Mother"},
        {"name": "No phone"},
        {"id": "g2", "name": "Ravi", "phone": "9876500002"},
    ]
    res = client.post("/api/user/guardians", json={"guardians": guardians}, headers=_auth(token))
    saved = res.json()["guardians"]
    assert [g["name"] for g in saved] == ["Mom", "Ravi"]
    assert saved[0]["id"] == "g1" and saved[1]["relation"] == "Guardian"

    profile = client.get("/api/user/profile", headers=_auth(token)).json()["user"]
    assert len(profile["guardians"]) == 2


def test_sos_dispatch_and_tracking(client):
    token, _ = _register(client)
    session_id = uuid.uuid4().hex

    assert client.post("/emergency_dispatch", json={**PUNE, "session_id": session_id}).status_code == 401

    res = client.post(
        "/emergency_dispatch",
        json={**PUNE, "session_id": session_id, "trigger_reason": "Manual SOS",
              "contacts": [{"name": "Mom", "phone": "9876500001"}]},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] and body["tracking_session_id"] == session_id
    assert body["live_tracking_url"].endswith(f"/track/{session_id}")
    assert body["sms_status"][0]["status"] == "not_sent_twilio_not_configured"
    assert body["nearest_police_stations"], "bundled police dataset should cover Pune"

    upd = client.post("/tracking/update", json={"session_id": session_id, "latitude": 18.521, "longitude": 73.857,
                                                "battery": "60%"}, headers=_auth(token))
    assert upd.status_code == 200

    data = client.get(f"/tracking/{session_id}").json()
    assert data["is_active"] and data["is_emergency"]
    assert data["latest_location"]["latitude"] == 18.521
    assert len(data["location_history"]) == 2

    page = client.get(f"/track/{session_id}")
    assert page.status_code == 200 and session_id in page.text

    # Another account cannot write into this session
    other, _ = _register(client)
    hijack = client.post("/tracking/update", json={"session_id": session_id, **PUNE}, headers=_auth(other))
    assert hijack.status_code == 403

    assert client.post(f"/tracking/{session_id}/stop", headers=_auth(token)).status_code == 200
    assert client.get(f"/tracking/{session_id}").json()["is_active"] is False
    ended = client.post("/tracking/update", json={"session_id": session_id, **PUNE}, headers=_auth(token))
    assert ended.status_code == 410

    mine = client.get("/api/incidents", headers=_auth(token)).json()["incidents"]
    assert len(mine) == 1 and mine[0]["trigger"] == "Manual SOS"


def test_live_tracking_without_sos(client):
    token, _ = _register(client)
    session_id = uuid.uuid4().hex
    res = client.post("/tracking/update", json={"session_id": session_id, **PUNE}, headers=_auth(token))
    assert res.status_code == 200
    assert client.get(f"/tracking/{session_id}").json()["is_emergency"] is False
    assert client.get("/tracking/doesnotexist0000000").status_code == 404
    assert client.post("/tracking/update", json={"session_id": "short", **PUNE}, headers=_auth(token)).status_code == 422


def test_dispatch_rate_limit_still_records(client):
    token, _ = _register(client)
    statuses = []
    for _ in range(7):
        res = client.post("/emergency_dispatch", json={**PUNE, "contacts": [{"phone": "9876500001"}]}, headers=_auth(token))
        assert res.status_code == 200
        statuses.append(res.json()["sms_status"][0]["status"])
    assert statuses[-1] == "skipped_rate_limited"
    assert len(client.get("/api/incidents", headers=_auth(token)).json()["incidents"]) == 7


def test_police_dashboard_requires_admin(client):
    assert client.get("/police_dashboard").status_code == 401
    assert client.get("/police_dashboard", auth=("admin", "wrong")).status_code == 401
    res = client.get("/police_dashboard", auth=("admin", "admin-pass"))
    assert res.status_code == 200 and "SOS alerts" in res.text
    assert client.get("/admin/incidents", auth=("admin", "admin-pass")).status_code == 200


def test_police_nearest_and_voice_phrase(client):
    res = client.post("/police/nearest", json={**PUNE, "count": 3})
    stations = res.json()["stations"]
    assert len(stations) == 3 and stations[0]["distance_km"] <= stations[1]["distance_km"]

    sos = client.post("/voice_sos", json={"phrase": "bachao"}).json()
    assert sos["sos_triggered"] is True
    calm = client.post("/voice_sos", json={"phrase": "hello there"}).json()
    assert calm["sos_triggered"] is False


def test_validation_errors_are_readable(client):
    res = client.post("/police/nearest", json={"latitude": 999, "longitude": 0})
    assert res.status_code == 422 and res.json()["success"] is False
    res = client.post("/predict_risk", json={})
    assert res.status_code == 422 and "latitude" in res.json()["error"]
