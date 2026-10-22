"""
Crime Risk Model (India-wide)
SurakshaX – AI-Based Women Safety Platform

Random Forest classifier over LOCATION-INDEPENDENT features, so it works in any Indian
city instead of memorising Pune coordinates:

    [time_of_day_bin (0-5), day_of_week (0-6), street_lighting (0-1),
     activity_density (0-1), police_distance_km (0-15)]

At prediction time the location features come from OpenStreetMap around the point
(geo_service.py): street lamps + busy streets -> lighting, shops/amenities -> activity
(how many people are around), and the nearest police station (bundled India-wide dataset).

Risk categories: Low (< 0.38), Medium (0.38 - 0.68), High (>= 0.68).

IMPORTANT: training labels are synthetic, produced by the documented heuristic in
_ground_truth_risk() (night-time, darkness, isolation and distance from police raise
risk). Replace generate_training_data() with real incident data (e.g. geocoded FIR /
NCRB records) to make the scores evidence-based.
"""

import datetime
import json
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

import geo_service

FEATURES = ["time_of_day_bin", "day_of_week", "street_lighting", "activity_density", "police_distance_km"]
MODEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_rf_model.joblib")
POLICE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "india_police_stations.json")
MODEL_VERSION = "india-v2"

TIME_WINDOWS = ["Late Night (00-04)", "Early Morning (04-08)", "Morning (08-12)",
                "Afternoon (12-16)", "Evening (16-20)", "Night (20-24)"]
CATEGORIES = {0: "Low Risk", 1: "Medium Risk", 2: "High Risk"}


def get_time_of_day_bin(hour: int) -> int:
    """24 h -> 6 bins: 0 late night, 1 early morning, 2 morning, 3 afternoon, 4 evening, 5 night."""
    return min(5, max(0, hour // 4))


def _ground_truth_risk(time_bin, dow, lighting, density, police_km, noise=0.0):
    """Documented synthetic risk heuristic (see module docstring)."""
    night = time_bin in (0, 5)
    temporal = {0: 0.30, 1: 0.05, 2: -0.05, 3: -0.03, 4: 0.08, 5: 0.22}[time_bin]
    weekend = 0.04 if dow in (4, 5, 6) and night else 0.0
    darkness = (1.0 - lighting) * (0.30 if night else 0.08)
    isolation = (1.0 - density) * (0.22 if night else 0.10)
    police = min(police_km, 8.0) / 8.0 * 0.15
    risk = 0.18 + temporal + weekend + darkness + isolation + police + noise
    return float(np.clip(risk, 0.02, 0.98))


def generate_training_data(n_samples: int = 20000, seed: int = 42):
    rng = np.random.default_rng(seed)
    time_bins = rng.choice(6, n_samples, p=[0.12, 0.12, 0.18, 0.18, 0.22, 0.18])
    dows = rng.integers(0, 7, n_samples)
    density = rng.beta(1.6, 1.6, n_samples)
    # lighting correlates with activity (busy streets are lit) but not perfectly
    lighting = np.clip(0.75 * density + rng.normal(0.15, 0.2, n_samples), 0, 1)
    police_km = np.clip(rng.gamma(2.0, 1.5, n_samples), 0.05, 15)
    noise = rng.normal(0, 0.04, n_samples)

    X = np.column_stack([time_bins, dows, lighting, density, police_km])
    y_cont = np.array([_ground_truth_risk(int(time_bins[i]), int(dows[i]), lighting[i], density[i],
                                          police_km[i], noise[i]) for i in range(n_samples)])
    y = np.where(y_cont < 0.38, 0, np.where(y_cont < 0.68, 1, 2))
    return X, y, y_cont


def _load_police():
    try:
        with open(POLICE_FILE, encoding="utf-8") as f:
            data = json.load(f)["stations"]
        for st in data:  # some OSM names are signs/notes rather than station names
            name = st.get("name", "")
            if len(name) > 60 or "no entry" in name.lower():
                st["name"] = "Police Station"
            st["phone"] = st.get("phone") or "112"
        return data, np.array([(s["lat"], s["lon"]) for s in data], dtype=float)
    except Exception:
        return [], np.zeros((0, 2))


class CrimeHotspotPredictor:
    def __init__(self):
        self.model = None
        self.police, self.police_xy = _load_police()
        self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(MODEL_FILE):
            try:
                model = joblib.load(MODEL_FILE)
                if getattr(model, "n_features_in_", None) == len(FEATURES):
                    self.model = model
                    return
            except Exception:
                pass
        X, y, _ = generate_training_data()
        rf = RandomForestClassifier(n_estimators=120, max_depth=12, min_samples_split=4,
                                    random_state=42, class_weight="balanced", n_jobs=1)
        rf.fit(X, y)
        self.model = rf
        try:
            joblib.dump(rf, MODEL_FILE, compress=3)
        except Exception:
            pass

    # ---------------------------------------------------------------- features
    def police_distance_km(self, lat, lon):
        if len(self.police_xy) == 0:
            return 15.0, None
        d = geo_service.haversine_km(lat, lon, self.police_xy[:, 0], self.police_xy[:, 1])
        i = int(np.argmin(d))
        return float(min(d[i], 15.0)), self.police[i]

    def nearest_police(self, lat, lon, top_k=2):
        if len(self.police_xy) == 0:
            return []
        d = geo_service.haversine_km(lat, lon, self.police_xy[:, 0], self.police_xy[:, 1])
        out = []
        for i in np.argsort(d)[:top_k]:
            s = dict(self.police[i])
            s["distance_km"] = round(float(d[i]), 2)
            out.append(s)
        return out

    def location_features(self, points, area=None, fetch=True):
        """(lighting, density, police_km, source) for each point."""
        pts = [(float(a), float(b)) for a, b in points]
        if area is None and fetch:
            area = geo_service.fetch_area(pts[:: max(1, len(pts) // 60)] or pts, radius_m=600, timeout_s=12)
        lighting, density, _ = geo_service.features_at(pts, area)
        police_km = np.array([self.police_distance_km(a, b)[0] for a, b in pts])
        return lighting, density, police_km, ("openstreetmap" if area is not None else "defaults (map data unavailable)")

    # ---------------------------------------------------------------- prediction
    def predict_batch(self, lighting, density, police_km, timestamp=None):
        timestamp = timestamp or datetime.datetime.now()
        tb = get_time_of_day_bin(timestamp.hour)
        dow = timestamp.weekday()
        n = len(lighting)
        X = np.column_stack([np.full(n, tb), np.full(n, dow), lighting, density, police_km])
        probs = self.model.predict_proba(X)
        risk = probs[:, 0] * 0.18 + probs[:, 1] * 0.50 + probs[:, 2] * 0.85
        return risk, probs

    def predict(self, lat: float, lon: float, timestamp: datetime.datetime = None,
                lighting: float = None, density: float = None):
        """
        Risk for one location. lighting/density may be supplied by the client; otherwise
        they are derived from OpenStreetMap around the point.
        """
        timestamp = timestamp or datetime.datetime.now()
        source = "client"
        if lighting is None or density is None:
            l_arr, d_arr, _, source = self.location_features([(lat, lon)])
            lighting = float(l_arr[0]) if lighting is None else lighting
            density = float(d_arr[0]) if density is None else density
        police_km, station = self.police_distance_km(lat, lon)

        risk, probs = self.predict_batch(np.array([lighting]), np.array([density]), np.array([police_km]), timestamp)
        probs = probs[0]
        pred = int(np.argmax(probs))
        tb = get_time_of_day_bin(timestamp.hour)
        police_txt = f"{station['name']} (~{police_km:.1f} km)" if station else "No mapped station nearby – dial 112"
        return {
            "risk_score": round(float(risk[0]), 3),
            "category": CATEGORIES[pred],
            "confidence": round(float(probs[pred]), 3),
            "probabilities": {"low": round(float(probs[0]), 3), "medium": round(float(probs[1]), 3),
                              "high": round(float(probs[2]), 3)},
            "factors": {
                "time_window": TIME_WINDOWS[tb],
                "street_lighting": "Adequate" if lighting >= 0.6 else ("Moderate" if lighting >= 0.35 else "Poor / Insufficient"),
                "population_density": "Busy / Active" if density >= 0.5 else ("Moderate" if density >= 0.2 else "Isolated / Low Activity"),
                "nearest_police": police_txt,
                # kept for older clients
                "nearest_hotspot_proximity": police_txt,
            },
            "features": {"lighting": round(float(lighting), 3), "density": round(float(density), 3),
                         "police_distance_km": round(police_km, 2)},
            "data_source": source,
            "model_version": MODEL_VERSION,
        }

    def get_grid_hotspots(self, center_lat: float = 18.52, center_lon: float = 73.86,
                          radius_km: float = 2.5, step_km: float = 0.5):
        """Risk grid around a centre point (any city) for the heat-map overlay."""
        lat_step = step_km / 111.0
        lon_step = step_km / (111.0 * max(0.2, np.cos(np.radians(center_lat))))
        n = int(radius_km / step_km)
        cells = [(center_lat + i * lat_step, center_lon + j * lon_step)
                 for i in range(-n, n + 1) for j in range(-n, n + 1)]
        area = geo_service.fetch_area([(center_lat, center_lon)], radius_m=int(radius_km * 1000 + 500), timeout_s=20)
        lighting, density, police_km, source = self.location_features(cells, area=area, fetch=False)
        risk, probs = self.predict_batch(lighting, density, police_km)
        out = []
        for (lat, lon), r, p in zip(cells, risk, probs):
            out.append({"lat": round(lat, 5), "lon": round(lon, 5), "risk_score": round(float(r), 3),
                        "category": CATEGORIES[int(np.argmax(p))], "intensity": round(float(r), 2)})
        return out, source


_crime_predictor_instance = None


def get_crime_predictor():
    global _crime_predictor_instance
    if _crime_predictor_instance is None:
        _crime_predictor_instance = CrimeHotspotPredictor()
    return _crime_predictor_instance
