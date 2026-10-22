"""
SurakshaX – AI-Based Women Safety Backend Server
Autonomous AI Safety Platform

Architecture & Modules:
- Module 1: Crime Hotspot Detection & Safe Route Recommendation (Random Forest + Modified Dijkstra)
- Module 2: CNN Voice-Activated Distress Keyword Recognition
- Module 3: Real-Time GPS Tracking & Live Map Sharing (5-second streaming interval)
- Module 4: Automated Emergency Dispatch & Police Integration (Twilio SMS/Call + Haversine Police Locator)
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import base64
import datetime
import os

DIST_WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist_web")

from crime_model import get_crime_predictor
from safe_routing import get_safe_route_planner
from voice_engine import get_voice_classifier
from police_service import get_police_service
from tracking_service import get_tracking_manager, render_live_tracking_html
from web_ui import render_web_app_html
from auth_service import get_auth_service

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB audio uploads
# Render/Heroku terminate TLS at a proxy; trust X-Forwarded-* so tracking links use https://
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(app)  # Enable Cross-Origin Resource Sharing for Android Clients & Browsers

# Initialize Singletons on boot
crime_predictor = get_crime_predictor()
safe_route_planner = get_safe_route_planner()
voice_classifier = get_voice_classifier()
police_service = get_police_service()
tracking_manager = get_tracking_manager()
auth_service = get_auth_service()


# ---------------------------------------------------------------------------
# 1. Health & System Information / Web App
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    # If opened in a web browser, serve the real Expo React Native frontend if available
    if "text/html" in request.headers.get("Accept", "") and request.args.get("format") != "json":
        expo_index = os.path.join(DIST_WEB_DIR, "index.html")
        if os.path.exists(expo_index):
            return send_from_directory(DIST_WEB_DIR, "index.html")
        return render_web_app_html()

    return jsonify({
        "service": "AI-Based Women Safety System (SurakshaX)",
        "architecture": "Multi-Modal Sensor Telemetry & Spatiotemporal Safety Network",
        "paper_citation": "AI Autonomous Women Safety Platform (Research Architecture)",
        "institution": "SurakshaX AI Safety Labs",
        "status": "online",
        "version": "2.1",
        "modules": {
            "module_1_crime_hotspots": "Random Forest over time + OpenStreetMap lighting/activity/police features (India-wide)",
            "module_1_safe_routing": "OSRM road alternatives scored by w = alpha*d + (1-alpha)*r (default alpha=0.4)",
            "module_2_voice_sos": "4-Layer CNN on 40-dim MFCC, ONNX runtime (P >= 0.85)",
            "module_3_gps_tracking": "FusedLocationProvider 5-second streaming with live Leaflet web beacon",
            "module_4_emergency_dispatch": "Device SMS + optional Twilio + nearest police (OpenStreetMap, all India)"
        },
        "endpoints": [
            "POST /analyze_status",
            "POST /predict_risk",
            "GET  /hotspots",
            "POST /safe_route",
            "POST /voice_sos",
            "POST /police/nearest",
            "POST /emergency_dispatch",
            "POST /tracking/update",
            "GET  /tracking/<session_id>",
            "GET  /track/<session_id>",
            "GET  /police_dashboard",
            "GET  /app",
            "GET  /expo",
            "GET  /web"
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.1"}), 200


def _bearer_token():
    return request.headers.get("Authorization", "").replace("Bearer ", "").strip()


# Real Expo React Native Frontend Routes & Static Bundles
@app.route("/_expo/<path:filename>")
def serve_expo_static(filename):
    expo_dir = os.path.join(DIST_WEB_DIR, "_expo")
    return send_from_directory(expo_dir, filename)


@app.route("/assets/<path:filename>")
def serve_expo_assets(filename):
    assets_dir = os.path.join(DIST_WEB_DIR, "assets")
    return send_from_directory(assets_dir, filename)


@app.route("/favicon.ico")
def serve_favicon():
    return send_from_directory(DIST_WEB_DIR, "favicon.ico")


@app.route("/app", methods=["GET"])
@app.route("/expo", methods=["GET"])
def expo_application():
    expo_index = os.path.join(DIST_WEB_DIR, "index.html")
    if os.path.exists(expo_index):
        return send_from_directory(DIST_WEB_DIR, "index.html")
    return render_web_app_html()


@app.route("/interactive", methods=["GET"])
@app.route("/web", methods=["GET"])
@app.route("/simulator", methods=["GET"])
def web_application():
    return render_web_app_html()


# ---------------------------------------------------------------------------
# 1.5. User Authentication & Profile API
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "")
        password = data.get("password", "")
        name = data.get("name", "")
        phone = data.get("phone", "")
        gender = data.get("gender", "Female")
        blood = data.get("blood_group", "O+")

        res = auth_service.register(email, password, name, phone, gender, blood)
        status_code = 200 if res.get("success") else 400
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email", "")
        password = data.get("password", "")

        res = auth_service.login(email, password)
        status_code = 200 if res.get("success") else 401
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/user/profile", methods=["GET"])
def api_user_profile():
    user = auth_service.get_user_by_token(_bearer_token())
    if user:
        return jsonify({"success": True, "user": user}), 200
    return jsonify({"success": False, "error": "Invalid or expired session"}), 401


@app.route("/api/user/guardians", methods=["POST"])
def api_update_guardians():
    try:
        data = request.get_json(force=True) or {}
        guardians = data.get("guardians", [])
        res = auth_service.update_guardians(_bearer_token(), guardians)
        return jsonify(res), 200 if res.get("success") else 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# 2. Multi-Modal Sensor Telemetry Inference (HDT)
# ---------------------------------------------------------------------------
@app.route("/analyze_status", methods=["POST"])
def analyze_status():
    """
    Accepts telemetry JSON from SurakshaX Android App:
    {
        "audio_score": float (0.0 - 1.0),
        "fall_force": float (1.0 - 10.0),
        "heart_rate": float (BPM),
        "latitude": float,
        "longitude": float
    }
    """
    try:
        data = request.get_json(force=True)
        # Also accept the legacy native-Android field names (audio_val / fall_val / hr_val)
        audio = float(data.get("audio_score", data.get("audio_val", 0.0)))
        fall = float(data.get("fall_force", data.get("fall_val", 0.0)))
        hr = float(data.get("heart_rate", data.get("hr_val", 70.0)))
        lat = float(data.get("latitude", 18.4550))
        lon = float(data.get("longitude", 73.9050))

        # Check real-time crime hotspot risk for the user's location
        risk_data = crime_predictor.predict(lat, lon)
        is_high_risk_zone = risk_data["category"] == "High Risk"

        # Hierarchical Decision Tree Logic
        is_scream = audio >= 0.70
        is_fall = fall >= 3.0
        is_stress = hr >= 120.0 or hr <= 45.0

        if is_scream:
            decision = "CRITICAL"
            reason = "Acoustic distress / distress vocalization detected"
        elif is_fall and is_stress:
            decision = "CRITICAL"
            reason = "Severe physical fall combined with acute physiological distress"
        elif is_fall:
            decision = "CRITICAL"
            reason = "High-impact fall / physical trauma detected"
        elif is_stress and (audio >= 0.50 or is_high_risk_zone):
            decision = "CRITICAL"
            reason = f"Elevated stress in a {risk_data['category']} environment"
        else:
            decision = "SAFE"
            reason = "Vitals and ambient signals within normal thresholds"

        return jsonify({
            "decision": decision,
            "reason": reason,
            # legacy native-Android client fields
            "next_screen": "Alerts" if decision == "CRITICAL" else "Happy_Screen",
            "risk_percent": int(round(max(audio, min(1.0, fall / 5.0)) * 100)),
            "message": reason,
            "location_risk": risk_data,
            "location": {"latitude": lat, "longitude": lon},
            "metrics": {
                "audio_score": audio,
                "fall_force": fall,
                "heart_rate": hr
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": "Invalid telemetry payload", "details": str(e)}), 400


# ---------------------------------------------------------------------------
# 3. Module 1: Crime Hotspot Detection (Random Forest Classifier)
# ---------------------------------------------------------------------------
@app.route("/predict_risk", methods=["POST"])
def predict_risk():
    """
    Accepts latitude and longitude, evaluates Random Forest spatiotemporal risk.
    """
    try:
        data = request.get_json(force=True)
        lat = float(data.get("latitude", 18.4550))
        lon = float(data.get("longitude", 73.9050))
        # Optional overrides; normally derived from OpenStreetMap around the point
        lighting = data.get("lighting")
        density = data.get("density")
        result = crime_predictor.predict(
            lat, lon,
            lighting=float(lighting) if lighting is not None else None,
            density=float(density) if density is not None else None,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/hotspots", methods=["GET"])
def get_hotspots():
    """
    Crime-risk grid around ?lat=&lon= (any location in India) for the heat-map overlay.
    """
    lat = float(request.args.get("lat", 18.5204))
    lon = float(request.args.get("lon", 73.8567))
    radius_km = min(float(request.args.get("radius_km", 2.5)), 5.0)
    step_km = max(float(request.args.get("step_km", 0.5)), 0.25)
    hotspots, source = crime_predictor.get_grid_hotspots(lat, lon, radius_km=radius_km, step_km=step_km)
    return jsonify({
        "center": {"latitude": lat, "longitude": lon},
        "grid_resolution": f"{int(step_km * 1000)}m x {int(step_km * 1000)}m",
        "total_cells": len(hotspots),
        "data_source": source,
        "hotspots": hotspots
    }), 200


# ---------------------------------------------------------------------------
# 4. Module 1 (Part 2): Safe Route Recommendation (Modified Dijkstra)
# ---------------------------------------------------------------------------
@app.route("/safe_route", methods=["POST"])
def safe_route():
    """
    Accepts:
    {
        "origin_lat": float,
        "origin_lon": float,
        "dest_lat": float,
        "dest_lon": float,
        "alpha": float (optional, default 0.4)
    }
    Returns safe route, shortest route, distance and risk trade-off comparisons.
    """
    try:
        data = request.get_json(force=True)
        origin = data.get("origin") or {}
        dest = data.get("destination") or {}
        start_lat = float(origin.get("latitude", data.get("origin_lat", 18.4550)))  # KJ College default
        start_lon = float(origin.get("longitude", data.get("origin_lon", 73.9050)))
        end_lat = float(dest.get("latitude", data.get("dest_lat", 18.5314)))       # Shivajinagar default
        end_lon = float(dest.get("longitude", data.get("dest_lon", 73.8446)))
        alpha = float(data.get("alpha", 0.4))

        routing_result = safe_route_planner.plan_route(start_lat, start_lon, end_lat, end_lon, alpha=alpha)
        return jsonify(routing_result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/geocode", methods=["GET"])
def geocode_address():
    """Address search inside India (OpenStreetMap Nominatim). ?q=...&lat=&lon= (lat/lon optional bias)."""
    import geo_service
    q = request.args.get("q", "")
    near = None
    if request.args.get("lat") and request.args.get("lon"):
        near = (float(request.args["lat"]), float(request.args["lon"]))
    results = geo_service.geocode(q, near=near)
    if results is None:
        return jsonify({"error": "Address search service unavailable, try again shortly", "results": []}), 503
    return jsonify({"query": q, "results": results}), 200


# ---------------------------------------------------------------------------
# 5. Module 2: CNN Voice-Activated SOS Recognition
# ---------------------------------------------------------------------------
@app.route("/voice_sos", methods=["POST"])
def voice_sos():
    """
    Accepts:
    {
        "phrase": str (e.g. "Bachao", "Help", "Madat kara", "Save me"),
        "audio_score": float (optional, 0.0 - 1.0),
        "noise_condition": str ("quiet"|"office"|"street"|"crowd"|"extreme")
    }
    Evaluates 4-layer CNN posterior probability. Triggers SOS if P > 0.85.

    Real audio can be sent either as multipart/form-data field "audio" (file)
    or as JSON {"audio_base64": "...", "audio_format": "m4a"}; it is then
    classified by the trained CNN (models/voice_cnn.onnx).
    """
    try:
        if "audio" in request.files:
            f = request.files["audio"]
            suffix = os.path.splitext(f.filename or "")[1] or ".m4a"
            return jsonify(voice_classifier.classify_audio_bytes(f.read(), suffix=suffix)), 200

        data = request.get_json(force=True)
        if data.get("audio_base64"):
            fmt = str(data.get("audio_format", "m4a")).lstrip(".")
            audio_bytes = base64.b64decode(data["audio_base64"])
            return jsonify(voice_classifier.classify_audio_bytes(audio_bytes, suffix=f".{fmt}")), 200

        phrase = data.get("phrase", "")
        audio_score = float(data.get("audio_score", 0.0))
        noise_condition = data.get("noise_condition", "street")

        result = voice_classifier.classify_audio_phrase(
            text_or_transcript=phrase,
            audio_score=audio_score,
            noise_env=noise_condition
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# 6. Module 4: Police Station Identification (Haversine Formula)
# ---------------------------------------------------------------------------
@app.route("/police/nearest", methods=["POST"])
def nearest_police():
    """
    Calculates the 2 nearest police stations using the Haversine formula.
    """
    try:
        data = request.get_json(force=True)
        lat = float(data.get("latitude", 18.4550))
        lon = float(data.get("longitude", 73.9050))
        count = max(1, min(int(data.get("count", 2)), 20))

        nearest = police_service.get_nearest_police_stations(lat, lon, top_k=count)
        return jsonify({
            "query_location": {"latitude": lat, "longitude": lon},
            "nearest_police_stations": nearest,
            "stations": nearest
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# 7. Module 4: Automated Emergency Dispatch Sequence
# ---------------------------------------------------------------------------
@app.route("/emergency_dispatch", methods=["POST"])
def emergency_dispatch():
    """
    Executes the 4-step emergency sequence specified in Section IV-E:
    (i) Dispatches SMS alerts with name, coordinates, and live tracking URL
    (ii) Initiates automated voice call to primary contact
    (iii) Identifies two nearest police stations using Haversine formula
    (iv) Dispatches structured alert payload to police email & dashboard
    """
    try:
        data = request.get_json(force=True)
        user_name = data.get("user_name", "Registered User")
        lat = float(data.get("latitude", 18.4550))
        lon = float(data.get("longitude", 73.9050))
        trigger_reason = data.get("trigger_reason", "Voice SOS")
        contacts = [c for c in (data.get("contacts") or []) if c.get("phone")]

        # Create active live tracking session for this emergency
        client_session = str(data.get("session_id") or "").strip() or None
        session = tracking_manager.get_session(client_session) if client_session else None
        if session:
            tracking_manager.update_location(client_session, lat, lon)
        else:
            session = tracking_manager.create_session(user_name=user_name, initial_lat=lat, initial_lon=lon, session_id=client_session)
        host_url = request.host_url.rstrip("/")
        tracking_url = f"{host_url}/track/{session['session_id']}"

        # Execute the 4-step dispatch
        dispatch_report = police_service.dispatch_emergency_alert(
            user_name=user_name,
            lat=lat,
            lon=lon,
            contacts=contacts,
            tracking_url=tracking_url,
            trigger_reason=trigger_reason
        )

        dispatch_report["tracking_session_id"] = session["session_id"]
        return jsonify(dispatch_report), 200

    except Exception as e:
        return jsonify({"error": "Failed to dispatch emergency alert", "details": str(e)}), 400


# ---------------------------------------------------------------------------
# 8. Module 3: Real-Time GPS Tracking & Live Map Sharing
# ---------------------------------------------------------------------------
@app.route("/tracking/update", methods=["POST"])
def tracking_update():
    """
    Streamed by Android FusedLocationProviderClient at 5-second intervals.
    """
    try:
        data = request.get_json(force=True)
        session_id = data.get("session_id")
        lat = float(data.get("latitude", 18.4550))
        lon = float(data.get("longitude", 73.9050))
        accuracy = float(data.get("accuracy", 5.0))
        speed = float(data.get("speed", 0.0))
        battery = data.get("battery", "85%")

        if not session_id:
            # Create session if client didn't supply one
            new_session = tracking_manager.create_session(
                user_name=data.get("user_name", "Emergency User"),
                initial_lat=lat,
                initial_lon=lon
            )
            session_id = new_session["session_id"]

        updated = tracking_manager.update_location(
            session_id=session_id,
            lat=lat,
            lon=lon,
            accuracy=accuracy,
            speed=speed,
            battery=battery,
            user_name=data.get("user_name")
        )
        return jsonify({
            "status": "updated",
            "session_id": session_id,
            "stream_interval_seconds": 5,
            "latest_point": updated["latest_location"]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/tracking/<session_id>", methods=["GET"])
def get_tracking_data(session_id):
    """
    Returns live tracking coordinates and history as JSON.
    """
    session = tracking_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Tracking session not found or expired"}), 404
    return jsonify(session), 200


@app.route("/track/<session_id>", methods=["GET"])
def live_map_view(session_id):
    """
    Section IV-D: Authorized emergency contacts receive a secure time-limited URL
    that renders the user's live position on an interactive map interface,
    enabling real-time remote monitoring WITHOUT requiring the contact to install an app.
    """
    session = tracking_manager.get_session(session_id)
    if not session:
        # Fallback demo session so clicking link always renders
        tracking_manager.create_session(user_name="Emergency User", initial_lat=18.4550, initial_lon=73.9050, session_id=session_id)

    html_content = render_live_tracking_html(session_id, request.host_url.rstrip("/"))
    return render_template_string(html_content)


# ---------------------------------------------------------------------------
# 9. Police Station Live Incident Dashboard
# ---------------------------------------------------------------------------
@app.route("/police_dashboard", methods=["GET"])
def police_dashboard():
    """
    Section IV-E (iv): Web-based incident management dashboard for police stations.
    """
    incidents = police_service.get_police_dashboard_incidents()
    cards_html = ""
    for inc in incidents:
        stations = inc.get("nearest_police_stations", [])
        station_name = stations[0].get("name", "N/A") if stations else "N/A"
        station_dist = stations[0].get("distance_km", "0") if stations else "0"
        station_phone = stations[0].get("phone", "112") if stations else "112"
        coords = inc.get("coordinates", {})
        lat_val = coords.get("latitude", "N/A")
        lon_val = coords.get("longitude", "N/A")

        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span style="color: #F87171;">{inc.get("incident_id")} • {inc.get("user_name")}</span>
                <span style="color: #FCD34D;">Trigger: {inc.get("trigger_source")}</span>
            </div>
            <div class="card-body">
                <div><strong>Timestamp:</strong> {inc.get("timestamp")}</div>
                <div><strong>Live Coordinates:</strong> {lat_val}, {lon_val}</div>
                <div><strong>Assigned Nearest Station:</strong> {station_name} ({station_dist} km away)</div>
            </div>
            <a class="btn" href="{inc.get("live_tracking_url")}" target="_blank">📡 Open Live GPS Map</a>
            <a class="btn" style="background: #059669; margin-left: 8px;" href="tel:{station_phone}">📞 Dispatch Patrol</a>
        </div>
        """

    content = cards_html if cards_html else '<div class="empty">No active emergency alerts at this moment. System in 24/7 autonomous monitoring mode.</div>'
    header_count = f"{len(incidents)} Active Emergencies"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pune Police Emergency Response Dashboard • SurakshaX</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0F172A; color: #F8FAFC; margin: 0; padding: 20px; }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }}
        h1 {{ font-size: 1.4rem; color: #38BDF8; margin: 0; }}
        .badge {{ background: #EF4444; color: white; padding: 4px 12px; border-radius: 9999px; font-weight: bold; font-size: 0.85rem; }}
        .card {{ background: #1E293B; border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 5px solid #EF4444; }}
        .card-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: bold; }}
        .card-body {{ font-size: 0.9rem; line-height: 1.5; color: #94A3B8; }}
        .btn {{ display: inline-block; background: #0284C7; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; margin-top: 8px; font-weight: 600; }}
        .empty {{ text-align: center; color: #64748B; padding: 40px; }}
    </style>
</head>
<body>
    <header>
        <h1>🚨 Emergency Response Center • SurakshaX Incident Feed</h1>
        <span class="badge">{header_count}</span>
    </header>
    <div>
        {content}
    </div>
</body>
</html>
    """
    return render_template_string(html)


# ---------------------------------------------------------------------------
# Server Launch
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print(f" SurakshaX AI-Based Women Safety Platform Backend")
    print(f" Port: {port} | All 4 Research Paper Modules Initialized & Active")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)
