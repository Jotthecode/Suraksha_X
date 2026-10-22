import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(name, payload, expected_decision):
    url = f"{BASE_URL}/analyze_status"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            decision = result.get("decision")
            print(f"[{'PASS' if decision == expected_decision else 'FAIL'}] {name}:")
            print(f"       Sent: {payload}")
            print(f"       Result: decision='{decision}', reason='{result.get('reason')}'\n")
            return decision == expected_decision
    except Exception as e:
        print(f"[FAIL] {name}: Could not connect to {url}. Is the Flask server running? Error: {e}\n")
        return False

if __name__ == "__main__":
    print("Testing SurakshaX Local Flask Backend...\n")
    
    # 1. Health check
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as response:
            res = json.loads(response.read().decode("utf-8"))
            print(f"[PASS] Health check: {res}\n")
    except Exception as e:
        print(f"[ERROR] Flask server is not running on {BASE_URL}. Run 'python app.py' first.\n")
        sys.exit(1)

    # 2. Test Safe Case
    safe_case = {
        "audio_score": 0.15,
        "fall_force": 1.2,
        "heart_rate": 72,
        "latitude": 22.7196,
        "longitude": 75.8577
    }
    test_endpoint("Safe Scenario (Normal Activity)", safe_case, "SAFE")

    # 3. Test Scream Critical Case
    scream_case = {
        "audio_score": 0.85,
        "fall_force": 1.1,
        "heart_rate": 80,
        "latitude": 22.7196,
        "longitude": 75.8577
    }
    test_endpoint("Scream Distress Scenario (ESC-50)", scream_case, "CRITICAL")

    # 4. Test Fall + Tachycardia Critical Case
    fall_case = {
        "audio_score": 0.20,
        "fall_force": 4.8,
        "heart_rate": 135,
        "latitude": 22.7196,
        "longitude": 75.8577
    }
    test_endpoint("Severe Fall & Stress Scenario (SisFall + SWELL-KW)", fall_case, "CRITICAL")
