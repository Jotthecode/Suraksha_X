"""
India-wide geographic data for SurakshaX, from OpenStreetMap.

- Overpass API: police stations, street lamps and activity (shops / amenities) around a
  point or along a route corridor. These feed the location-independent crime-risk model
  and the police locator, so everything works in any Indian city, not just Pune.
- OSRM: real road routes (walking first, driving fallback) with alternatives, scored by
  the safe-route planner.

All calls are cached in memory and fail soft (return None) so the API never crashes when
a public endpoint is slow or rate-limited.
"""

import math
import threading
import time

import numpy as np
import requests

try:  # Use the OS certificate store (needed behind TLS-inspecting proxies; harmless elsewhere)
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

USER_AGENT = "SurakshaX/2.1 (women-safety research app; https://github.com/)"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OSRM_PROFILES = [
    ("foot", "https://routing.openstreetmap.de/routed-foot/route/v1/driving"),
    ("car", "https://router.project-osrm.org/route/v1/driving"),
]

LAMP_RADIUS_M = 250      # street lamps counted within this radius -> lighting
ACTIVITY_RADIUS_M = 400  # shops / amenities within this radius -> activity (people around)
POLICE_SEARCH_M = 10000

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


class _TTLCache:
    def __init__(self, ttl_s=3600, max_items=512):
        self.ttl, self.max = ttl_s, max_items
        self._d = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            v = self._d.get(key)
            if v and time.time() - v[0] < self.ttl:
                return v[1]
            return None

    def set(self, key, value):
        with self._lock:
            if len(self._d) >= self.max:
                oldest = min(self._d, key=lambda k: self._d[k][0])
                self._d.pop(oldest, None)
            self._d[key] = (time.time(), value)


_area_cache = _TTLCache(ttl_s=6 * 3600)
_geocode_cache = _TTLCache(ttl_s=7 * 24 * 3600, max_items=2048)
_geocode_lock = threading.Lock()
_last_geocode = [0.0]
_police_cache = _TTLCache(ttl_s=24 * 3600)


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorised great-circle distance (km); lat2/lon2 may be numpy arrays."""
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(np.asarray(lon2) - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def overpass(query: str, timeout_s: int = 45, attempts: int = 3):
    """
    Run an Overpass QL query. Public servers often answer 429/504 when busy, so retry
    across mirrors with a short backoff.
    """
    for attempt in range(attempts):
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                r = _session.post(endpoint, data={"data": query}, timeout=timeout_s)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                    return r.json().get("elements", [])
            except Exception:
                continue
        time.sleep(1.5 * (attempt + 1))
    return None


def _around(radius_m, coords):
    flat = ",".join(f"{lat:.5f},{lon:.5f}" for lat, lon in coords)
    return f"(around:{int(radius_m)},{flat})"


def fetch_area(coords, radius_m=600, timeout_s=12, attempts=1):
    """
    Lamps, activity points and police stations around one or more points
    (a polyline of points = a route corridor). Returns dict of numpy arrays or None.
    """
    coords = [(float(a), float(b)) for a, b in coords]
    key = (tuple((round(a, 3), round(b, 3)) for a, b in coords), int(radius_m))
    cached = _area_cache.get(key)
    if cached is not None:
        return cached

    near = _around(radius_m, coords)
    police_near = _around(max(radius_m, POLICE_SEARCH_M), coords[:: max(1, len(coords) // 8)] or coords)
    query = f"""[out:json][timeout:35];
nwr["amenity"="police"]{police_near};
out center tags;
make lamps_marker;
out;
node["highway"="street_lamp"]{near};
out skel qt;
make activity_marker;
out;
(node["shop"]{near};node["amenity"]{near};);
out skel qt;"""
    elements = overpass(query, timeout_s=timeout_s, attempts=attempts)
    if elements is None:
        return None

    police, lamps, activity = [], [], []
    bucket = police
    for e in elements:
        t = e.get("type")
        if t == "lamps_marker":
            bucket = lamps
            continue
        if t == "activity_marker":
            bucket = activity
            continue
        if bucket is police:
            lat = e.get("lat", e.get("center", {}).get("lat"))
            lon = e.get("lon", e.get("center", {}).get("lon"))
            if lat is not None:
                police.append((lat, lon, e.get("tags", {}), e.get("id")))
        elif "lat" in e:
            bucket.append((e["lat"], e["lon"]))

    result = {
        "police": police,
        "lamps": np.array(lamps, dtype=float).reshape(-1, 2),
        "activity": np.array(activity, dtype=float).reshape(-1, 2),
    }
    _area_cache.set(key, result)
    return result


def features_at(points, area):
    """
    Location features for each (lat, lon) in `points` using a fetched area:
      lighting (0-1), density (0-1), police_km (nearest station, capped at 15 km).
    Street-lamp mapping in India is sparse, so busy commercial streets (high activity)
    also count as lit.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    n = len(pts)
    lighting = np.full(n, 0.5)
    density = np.full(n, 0.5)
    police_km = np.full(n, 3.0)
    if area is None:
        return lighting, density, police_km

    pol = np.array([(p[0], p[1]) for p in area["police"]], dtype=float).reshape(-1, 2)
    for i, (lat, lon) in enumerate(pts):
        lamps = area["lamps"]
        act = area["activity"]
        n_lamps = int(np.sum(haversine_km(lat, lon, lamps[:, 0], lamps[:, 1]) <= LAMP_RADIUS_M / 1000)) if len(lamps) else 0
        n_act = int(np.sum(haversine_km(lat, lon, act[:, 0], act[:, 1]) <= ACTIVITY_RADIUS_M / 1000)) if len(act) else 0
        density[i] = min(1.0, n_act / 40.0)
        lighting[i] = max(min(1.0, n_lamps / 8.0), 0.85 * density[i])
        police_km[i] = float(np.min(haversine_km(lat, lon, pol[:, 0], pol[:, 1]))) if len(pol) else 15.0
    return lighting, density, np.minimum(police_km, 15.0)


def _address(tags):
    parts = [tags.get(k) for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode")]
    return ", ".join(p for p in parts if p) or tags.get("addr:full", "")


def police_near(lat, lon, top_k=5):
    """Nearest police stations from OpenStreetMap (any city in India)."""
    key = (round(lat, 2), round(lon, 2))
    stations = _police_cache.get(key)
    if stations is None:
        stations = []
        for radius in (POLICE_SEARCH_M, 30000):
            els = overpass(f'[out:json][timeout:25];nwr["amenity"="police"](around:{radius},{lat:.5f},{lon:.5f});out center tags;')
            if els is None:
                return None  # Overpass unreachable
            for e in els:
                plat = e.get("lat", e.get("center", {}).get("lat"))
                plon = e.get("lon", e.get("center", {}).get("lon"))
                if plat is None:
                    continue
                tags = e.get("tags", {})
                stations.append({
                    "id": f"osm-{e.get('type', 'n')[0]}{e.get('id')}",
                    "name": tags.get("name:en") or tags.get("name") or "Police Station",
                    "lat": plat,
                    "lon": plon,
                    "phone": tags.get("phone") or tags.get("contact:phone") or "112",
                    "email": tags.get("email") or tags.get("contact:email") or "",
                    "address": _address(tags),
                    "source": "OpenStreetMap",
                })
            if stations:
                break
        _police_cache.set(key, stations)
    out = []
    for s in stations:
        s = dict(s)
        s["distance_km"] = round(float(haversine_km(lat, lon, s["lat"], s["lon"])), 2)
        out.append(s)
    out.sort(key=lambda s: s["distance_km"])
    return out[:top_k]


def osrm_routes(start, end, alternatives=3):
    """
    Road routes between (lat, lon) points. Walking profile first (the primary use case),
    driving as fallback. Returns (profile, [ {coords:[(lat,lon)], distance_km, duration_min} ]).
    """
    for profile, base in OSRM_PROFILES:
        url = f"{base}/{start[1]:.6f},{start[0]:.6f};{end[1]:.6f},{end[0]:.6f}"
        try:
            r = _session.get(url, params={"alternatives": alternatives, "overview": "full",
                                          "geometries": "geojson", "steps": "false"}, timeout=25)
            data = r.json()
        except Exception:
            continue
        if data.get("code") != "Ok" or not data.get("routes"):
            continue
        routes = [{
            "coords": [(c[1], c[0]) for c in rt["geometry"]["coordinates"]],
            "distance_km": rt["distance"] / 1000.0,
            "duration_min": rt["duration"] / 60.0,
        } for rt in data["routes"]]
        return profile, routes
    return None, []


def osrm_via(start, via, end, profile_base):
    """Single route forced through a via point (used to create alternatives)."""
    url = f"{profile_base}/{start[1]:.6f},{start[0]:.6f};{via[1]:.6f},{via[0]:.6f};{end[1]:.6f},{end[0]:.6f}"
    try:
        data = _session.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=25).json()
        if data.get("code") == "Ok" and data.get("routes"):
            rt = data["routes"][0]
            return {"coords": [(c[1], c[0]) for c in rt["geometry"]["coordinates"]],
                    "distance_km": rt["distance"] / 1000.0, "duration_min": rt["duration"] / 60.0}
    except Exception:
        pass
    return None


def sample_polyline(coords, step_km=0.15, max_points=150):
    """Evenly spaced points along a polyline."""
    if len(coords) < 2:
        return list(coords)
    pts = [coords[0]]
    carry = 0.0
    for (a_lat, a_lon), (b_lat, b_lon) in zip(coords[:-1], coords[1:]):
        seg = float(haversine_km(a_lat, a_lon, b_lat, b_lon))
        while carry + seg >= step_km and seg > 0:
            f = (step_km - carry) / seg
            a_lat, a_lon = a_lat + (b_lat - a_lat) * f, a_lon + (b_lon - a_lon) * f
            pts.append((a_lat, a_lon))
            seg = float(haversine_km(a_lat, a_lon, b_lat, b_lon))
            carry = 0.0
        carry += seg
    pts.append(coords[-1])
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts) - 1, max_points).astype(int)
        pts = [pts[i] for i in idx]
    return pts


def offset_point(lat, lon, bearing_deg, dist_km):
    """Point dist_km away from (lat, lon) along a bearing."""
    r = 6371.0
    br = math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(dist_km / r) + math.cos(p1) * math.sin(dist_km / r) * math.cos(br))
    l2 = l1 + math.atan2(math.sin(br) * math.sin(dist_km / r) * math.cos(p1),
                         math.cos(dist_km / r) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), math.degrees(l2)


def bearing(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def geocode(query: str, near=None, limit: int = 5):
    """
    Address search via OpenStreetMap Nominatim, restricted to India. Results near the
    user (if `near`=(lat, lon) is given) are ranked first. Respects Nominatim's
    1 request/second policy and caches results.
    """
    q = " ".join(query.split())[:200]
    if not q:
        return []
    key = (q.lower(), round(near[0], 1) if near else None, round(near[1], 1) if near else None)
    cached = _geocode_cache.get(key)
    if cached is not None:
        return cached
    params = {"q": q, "format": "jsonv2", "countrycodes": "in", "limit": limit, "addressdetails": 0}
    if near:
        # Prefer (not restrict to) a ~60 km box around the user
        d = 0.55
        params["viewbox"] = f"{near[1] - d},{near[0] + d},{near[1] + d},{near[0] - d}"
    with _geocode_lock:
        wait = 1.05 - (time.time() - _last_geocode[0])
        if wait > 0:
            time.sleep(wait)
        _last_geocode[0] = time.time()
        try:
            r = _session.get("https://nominatim.openstreetmap.org/search", params=params, timeout=15)
            items = r.json() if r.status_code == 200 else None
        except Exception:
            items = None
    if items is None:
        return None
    results = [{"name": it.get("display_name", ""), "lat": float(it["lat"]), "lon": float(it["lon"])} for it in items]
    if near:
        results.sort(key=lambda x: float(haversine_km(near[0], near[1], x["lat"], x["lon"])))
    _geocode_cache.set(key, results)
    return results
