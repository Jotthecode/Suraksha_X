"""
Safe Route Recommendation (India-wide)
SurakshaX – AI-Based Women Safety Platform

Route weight from the paper:  w(route) = alpha * d_norm + (1 - alpha) * r
  d_norm : route length / longest candidate length
  r      : mean crime-risk score sampled every ~150 m along the route
  alpha  : trade-off (default 0.4; 1.0 = shortest, lower = safer)

Candidate routes are real roads from OSRM (OpenStreetMap; walking profile, driving
fallback): the routing engine's alternatives plus detours forced through via-points on
either side of the direct line. Each candidate is scored with the India-wide crime model
(crime_model.py), so this works in any Indian city.
"""

import numpy as np

import geo_service
from crime_model import get_crime_predictor

HIGH_RISK = 0.66
MAX_ROUTE_KM = 60.0  # beyond this "safe walking route" is not meaningful


def _dedupe(routes):
    out = []
    for r in routes:
        if all(abs(r["distance_km"] - o["distance_km"]) > 0.05 or
               abs(len(r["coords"]) - len(o["coords"])) > 5 for o in out):
            out.append(r)
    return out


class SafeRoutePlanner:
    def __init__(self):
        self.crime = get_crime_predictor()

    def _candidates(self, start, end):
        profile, routes = geo_service.osrm_routes(start, end, alternatives=3)
        if not routes:
            return profile, []
        # Add detours through via-points left/right of the midpoint for more diverse options
        direct_km = float(geo_service.haversine_km(start[0], start[1], end[0], end[1]))
        if len(routes) < 3 and direct_km > 0.4:
            base = dict(geo_service.OSRM_PROFILES)[profile]
            mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            brg = geo_service.bearing(start, end)
            for side in (90, -90):
                via = geo_service.offset_point(mid[0], mid[1], brg + side, max(0.25, 0.2 * direct_km))
                r = geo_service.osrm_via(start, via, end, base)
                if r and r["distance_km"] < 1.6 * routes[0]["distance_km"]:
                    routes.append(r)
        return profile, _dedupe(routes)

    def _score(self, routes):
        samples = [geo_service.sample_polyline(r["coords"]) for r in routes]
        corridor = [p for s in samples for p in s[:: max(1, len(s) // 40)]]
        area = geo_service.fetch_area(corridor[:120], radius_m=450, timeout_s=25)
        source = "openstreetmap" if area is not None else "defaults (map data unavailable)"
        scored = []
        for r, pts in zip(routes, samples):
            lighting, density, police_km, _ = self.crime.location_features(pts, area=area, fetch=False)
            risk, _ = self.crime.predict_batch(lighting, density, police_km)
            scored.append({**r, "risk": risk, "points": pts})
        return scored, source

    def _describe(self, r, alpha, weight):
        risk = r["risk"]
        steps = []
        n = len(r["points"])
        for k in range(0, max(1, n - 1), max(1, n // 6)):
            seg = risk[k:k + max(1, n // 6)]
            mean = float(np.mean(seg)) if len(seg) else 0.0
            steps.append({
                "from_km": round(k * r["distance_km"] / max(1, n - 1), 2),
                "risk_score": round(mean, 2),
                "safety_rating": "Safe" if mean < 0.38 else ("Moderate" if mean < HIGH_RISK else "High Risk"),
            })
        return {
            "waypoints": [{"lat": round(a, 6), "lon": round(b, 6)} for a, b in r["coords"]],
            "steps": steps,
            "total_distance_km": round(r["distance_km"], 2),
            "duration_min": round(r["duration_min"], 1),
            "mean_risk_score": round(float(np.mean(risk)), 3),
            "max_risk_score": round(float(np.max(risk)), 3),
            "high_risk_segments": int(np.sum(risk >= HIGH_RISK)),
            "weight": round(weight, 4),
            "alpha": alpha,
        }

    def plan_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, alpha: float = 0.4):
        start, end = (start_lat, start_lon), (end_lat, end_lon)
        direct = float(geo_service.haversine_km(start_lat, start_lon, end_lat, end_lon))
        if direct > MAX_ROUTE_KM:
            return {"error": f"Destination is {direct:.0f} km away. Safe routing is designed for city trips "
                             f"(under {MAX_ROUTE_KM:.0f} km)."}
        profile, routes = self._candidates(start, end)
        if not routes:
            return {"error": "No road route found between these points (routing service unavailable or no road connection)."}

        scored, source = self._score(routes)
        max_d = max(r["distance_km"] for r in scored)
        weights = [alpha * (r["distance_km"] / max_d) + (1 - alpha) * float(np.mean(r["risk"])) for r in scored]
        safe_i = int(np.argmin(weights))
        short_i = int(np.argmin([r["distance_km"] for r in scored]))
        safe = self._describe(scored[safe_i], alpha, weights[safe_i])
        short = self._describe(scored[short_i], 1.0, weights[short_i])

        d_short, d_safe = short["total_distance_km"], safe["total_distance_km"]
        r_short, r_safe = short["mean_risk_score"], safe["mean_risk_score"]
        return {
            "origin": {"input_lat": start_lat, "input_lon": start_lon, "closest_node": "Start"},
            "destination": {"input_lat": end_lat, "input_lon": end_lon, "closest_node": "Destination"},
            "travel_mode": "walking" if profile == "foot" else "driving",
            "candidates_evaluated": len(scored),
            "data_source": source,
            "safe_route": safe,
            "shortest_route": short,
            "alternatives": [
                {"total_distance_km": round(r["distance_km"], 2), "mean_risk_score": round(float(np.mean(r["risk"])), 3),
                 "weight": round(w, 4)} for r, w in zip(scored, weights)
            ],
            "metrics_comparison": {
                "tradeoff_parameter_alpha": alpha,
                "safe_distance_km": d_safe,
                "shortest_distance_km": d_short,
                "distance_increase_percent": round((d_safe - d_short) / max(0.01, d_short) * 100, 1),
                "safe_mean_risk": r_safe,
                "shortest_mean_risk": r_short,
                "risk_reduction_percent": round(max(0.0, (r_short - r_safe) / max(0.01, r_short) * 100), 1),
            },
        }


_route_planner_instance = None


def get_safe_route_planner():
    global _route_planner_instance
    if _route_planner_instance is None:
        _route_planner_instance = SafeRoutePlanner()
    return _route_planner_instance
