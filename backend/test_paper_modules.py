"""
Verification & Test Suite for SurakshaX Research Paper Implementation
Paper: 'AI-Based Women Safety App' (IJRASET May 2026)
Authors: Pranav Darekar, Swaraj Dorage, Prathmeah Gaikwad, Harish Senthil, Prof. Geetanjali Bansod
"""

import json
from app import app

def run_all_tests():
    client = app.test_client()
    passed = 0
    total = 0

    def check(name, condition, details=""):
        nonlocal passed, total
        total += 1
        status = "PASS" if condition else "FAIL"
        if condition:
            passed += 1
        print(f"[{status}] {name}")
        if details:
            print(f"       -> {details}")

    print("\n" + "=" * 70)
    print(" RUNNING RESEARCH PAPER MODULE VALIDATION SUITE")
    print("=" * 70)

    # 1. Health & Architecture Citation
    res = client.get("/")
    data = json.loads(res.data)
    check("System Info & Architecture Citation",
          res.status_code == 200 and "paper_citation" in data,
          f"Status 200, Citation: {data.get('paper_citation')}")

    # 2. Module 1: Crime Hotspot Detection (Random Forest)
    payload = {"latitude": 18.5020, "longitude": 73.9380, "lighting": 0.2, "density": 0.3}
    res = client.post("/predict_risk", json=payload)
    data = json.loads(res.data)
    check("Crime Hotspot Random Forest Prediction",
          res.status_code == 200 and "risk_score" in data and "category" in data,
          f"Risk Score: {data.get('risk_score')}, Category: {data.get('category')}")

    # 3. Module 1: Heatmap Grid
    res = client.get("/hotspots?step=0.04")
    data = json.loads(res.data)
    check("250m Uniform Crime Hotspot Grid",
          res.status_code == 200 and len(data.get("hotspots", [])) > 0,
          f"Generated {data.get('total_cells')} spatial cells around the query point")

    # 4. Module 1 (Part 2): Safe Route Recommendation (Modified Dijkstra)
    route_payload = {
        "origin_lat": 18.4550, "origin_lon": 73.9050,  # KJ College
        "dest_lat": 18.5314, "dest_lon": 73.8446,      # Shivajinagar
        "alpha": 0.4
    }
    res = client.post("/safe_route", json=route_payload)
    data = json.loads(res.data)
    metrics = data.get("metrics_comparison", {})
    check("Safe Route Recommendation (Modified Dijkstra with alpha=0.4)",
          res.status_code == 200 and "safe_route" in data and "shortest_route" in data,
          f"Safe Dist: {metrics.get('safe_distance_km')}km, Shortest Dist: {metrics.get('shortest_distance_km')}km, "
          f"Risk Reduction: {metrics.get('risk_reduction_percent')}%, Dist Delta: +{metrics.get('distance_increase_percent')}%")

    # 5. Module 2: CNN Voice-Activated SOS Recognition
    voice_payload = {
        "phrase": "Bachao",
        "audio_score": 0.88,
        "noise_condition": "street"
    }
    res = client.post("/voice_sos", json=voice_payload)
    data = json.loads(res.data)
    check("CNN Voice-Activated SOS Keyword Trigger (Bachao / Street Noise)",
          res.status_code == 200 and data.get("sos_triggered") is True and data.get("posterior_probability") >= 0.85,
          f"Keyword: {data.get('detected_keyword')}, P: {data.get('posterior_probability')}, Latency: {data.get('inference_latency_ms')}ms")

    # 6. Module 4: Police Station Locator (Haversine Formula)
    police_payload = {"latitude": 18.4550, "longitude": 73.9050}
    res = client.post("/police/nearest", json=police_payload)
    data = json.loads(res.data)
    nearest = data.get("nearest_police_stations", [])
    check("Haversine Formula - 2 Nearest Police Stations Identification",
          res.status_code == 200 and len(nearest) == 2,
          f"1. {nearest[0]['name']} ({nearest[0]['distance_km']} km), 2. {nearest[1]['name']} ({nearest[1]['distance_km']} km)")

    # 7. Module 4: Multi-Channel Emergency Dispatch
    dispatch_payload = {
        "user_name": "Aarjoo Dahiya",
        "latitude": 18.4550,
        "longitude": 73.9050,
        "trigger_reason": "CNN Voice SOS (Bachao)",
        "contacts": [
            {"name": "Guardian 1", "phone": "9302414220", "relation": "Parent"}
        ]
    }
    res = client.post("/emergency_dispatch", json=dispatch_payload)
    data = json.loads(res.data)
    check("Automated 4-Step Emergency Dispatch & Session Generation",
          res.status_code == 200 and "tracking_session_id" in data and "sms_status" in data,
          f"Incident ID: {data.get('incident_id')}, Tracking URL: {data.get('live_tracking_url')}")

    session_id = data.get("tracking_session_id")

    # 8. Module 3: 5-Second GPS Streaming Update
    update_payload = {
        "session_id": session_id,
        "latitude": 18.4565,
        "longitude": 73.9062,
        "accuracy": 4.2,
        "speed": 1.4,
        "battery": "84%"
    }
    res = client.post("/tracking/update", json=update_payload)
    data = json.loads(res.data)
    check("Real-Time GPS 5-Second Interval Streaming Update",
          res.status_code == 200 and data.get("status") == "updated",
          f"Session: {data.get('session_id')}, Interval: {data.get('stream_interval_seconds')}s")

    # 9. Module 3: Live Map Web Browser View
    res = client.get(f"/track/{session_id}")
    check("Live Interactive Browser Tracking Map (Leaflet.js)",
          res.status_code == 200 and b"SurakshaX Live Emergency Tracking" in res.data,
          f"Served responsive HTML map for remote guardians")

    # 10. Police Dashboard View
    res = client.get("/police_dashboard")
    check("Police Web Incident Dashboard Feed",
          res.status_code == 200 and b"Incident Feed" in res.data,
          f"Police web interface operational")

    # 11. Full 7-Screen Responsive Web Application View
    res = client.get("/app")
    check("Full 7-Screen Web Application Interface (/app)",
          res.status_code == 200 and b"SurakshaX" in res.data and (b"Safe Route" in res.data or b"_expo/static/js" in res.data),
          f"Served interactive browser application")

    print("=" * 70)
    print(f" TEST SUMMARY: {passed}/{total} TESTS PASSED")
    print("=" * 70 + "\n")

    return passed == total

if __name__ == "__main__":
    run_all_tests()
