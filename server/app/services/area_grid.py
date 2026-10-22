"""
Bundled India-wide lighting / activity grid (data/india_area_grid.npz, built by
scripts/build_area_grid.py from an OpenStreetMap extract).

Gives the same lighting and density features as a live Overpass query (street lamps within
250 m, shops / amenities within 400 m, see geo.features_at), but from local data: instant,
offline, and immune to the public Overpass servers being overloaded.
"""

import math
import os
import threading

import numpy as np

from ..config import DATA_DIR

GRID_FILE = os.path.join(DATA_DIR, "india_area_grid.npz")

# Grid layout (shared with the build script)
LAT0, LON0 = 6.0, 68.0
CELL_DEG = 0.001
ROWS = int(round((37.5 - LAT0) / CELL_DEG))
COLS = int(round((97.5 - LON0) / CELL_DEG))

LAMP_RADIUS_KM = 0.25
ACTIVITY_RADIUS_KM = 0.40
KM_PER_DEG_LAT = 111.32
# Starts with "openstreetmap" so clients treat it like live OSM data
SOURCE_LABEL = "openstreetmap (bundled)"

_lock = threading.Lock()
_grid = None
_load_failed = False


def _load():
    global _grid, _load_failed
    if _grid is not None or _load_failed:
        return _grid
    with _lock:
        if _grid is None and not _load_failed:
            try:
                with np.load(GRID_FILE) as z:
                    _grid = {
                        "keys": z["keys"].astype(np.int64),
                        "lamps": z["lamps"].astype(np.int32),
                        "activity": z["activity"].astype(np.int32),
                        "source": str(z["source"][0]) if "source" in z else "",
                    }
            except (OSError, KeyError, ValueError):
                _load_failed = True
    return _grid


def available() -> bool:
    return _load() is not None


def info():
    g = _load()
    if g is None:
        return {"available": False}
    return {"available": True, "cells": int(len(g["keys"])), "lamps": int(g["lamps"].sum()),
            "activity": int(g["activity"].sum()), "source": g["source"]}


def _offsets(radius_km, mean_lat):
    """Cell offsets (drow, dcol) whose centres lie within radius_km of the centre cell."""
    lat_km = CELL_DEG * KM_PER_DEG_LAT
    lon_km = lat_km * max(0.2, math.cos(math.radians(mean_lat)))
    k = int(math.ceil(radius_km / lat_km))
    m = int(math.ceil(radius_km / lon_km))
    dr, dc = np.meshgrid(np.arange(-k, k + 1), np.arange(-m, m + 1), indexing="ij")
    inside = (dr * lat_km) ** 2 + (dc * lon_km) ** 2 <= radius_km ** 2
    return dr[inside], dc[inside]


def _sum_within(rows, cols, radius_km, mean_lat, values, keys):
    dr, dc = _offsets(radius_km, mean_lat)
    r = rows[:, None] + dr[None, :]
    c = cols[:, None] + dc[None, :]
    valid = (r >= 0) & (r < ROWS) & (c >= 0) & (c < COLS)
    flat = (r * COLS + c).ravel()
    idx = np.clip(np.searchsorted(keys, flat), 0, len(keys) - 1)
    hit = (keys[idx] == flat) & valid.ravel()
    counts = np.where(hit, values[idx], 0).reshape(r.shape)
    return counts.sum(axis=1)


def counts(points):
    """(lamps within 250 m, shops/amenities within 400 m) for each (lat, lon), or None without the grid."""
    g = _load()
    if g is None:
        return None
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts) == 0:
        return np.zeros(0), np.zeros(0)
    rows = np.floor((pts[:, 0] - LAT0) / CELL_DEG).astype(np.int64)
    cols = np.floor((pts[:, 1] - LON0) / CELL_DEG).astype(np.int64)
    mean_lat = float(np.mean(pts[:, 0]))
    lamps = _sum_within(rows, cols, LAMP_RADIUS_KM, mean_lat, g["lamps"], g["keys"])
    activity = _sum_within(rows, cols, ACTIVITY_RADIUS_KM, mean_lat, g["activity"], g["keys"])
    return lamps, activity


def features(points):
    """(lighting 0-1, density 0-1) per point with the same formula as geo.features_at, or None."""
    c = counts(points)
    if c is None:
        return None
    lamps, activity = c
    density = np.minimum(1.0, activity / 40.0)
    lighting = np.maximum(np.minimum(1.0, lamps / 8.0), 0.85 * density)
    return lighting, density
