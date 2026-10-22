"""Bundled lighting / activity grid: counts within the right radius and matches the live-data formula."""

import numpy as np
import pytest

from app.services import area_grid as ag


def _key(lat, lon):
    row = int((lat - ag.LAT0) / ag.CELL_DEG)
    col = int((lon - ag.LON0) / ag.CELL_DEG)
    return row * ag.COLS + col


@pytest.fixture
def tiny_grid(monkeypatch):
    lat, lon = 22.7185, 75.8555  # Rajwada, Indore
    cells = {
        _key(lat, lon): (4, 10),                # same cell: 4 lamps, 10 shops
        _key(lat + 0.0015, lon): (3, 0),        # ~170 m north: inside lamp radius
        _key(lat + 0.0035, lon): (0, 25),       # ~390 m north: only inside activity radius
        _key(lat + 0.0060, lon): (50, 50),      # ~670 m: outside both
    }
    keys = np.array(sorted(cells), dtype=np.int64)
    monkeypatch.setattr(ag, "_grid", {
        "keys": keys,
        "lamps": np.array([cells[k][0] for k in keys], dtype=np.int32),
        "activity": np.array([cells[k][1] for k in keys], dtype=np.int32),
        "source": "test",
    })
    return lat, lon


def test_counts_respect_radii(tiny_grid):
    lamps, activity = ag.counts([tiny_grid])
    assert lamps[0] == 7       # 4 + 3; the 670 m cell is excluded
    assert activity[0] == 35   # 10 + 25


def test_features_match_live_formula(tiny_grid):
    lighting, density = ag.features([tiny_grid, (10.0, 77.0)])
    assert density[0] == pytest.approx(35 / 40)
    assert lighting[0] == pytest.approx(max(7 / 8, 0.85 * 35 / 40))
    assert lighting[1] == 0 and density[1] == 0  # empty area -> dark and isolated


def test_risk_uses_grid_without_network(tiny_grid, monkeypatch):
    from app.services import geo
    from app.services.risk import get_crime_predictor

    monkeypatch.setattr(geo, "fetch_area", lambda *a, **k: pytest.fail("must not call Overpass"))
    result = get_crime_predictor().predict(*tiny_grid)
    assert result["data_source"] == ag.SOURCE_LABEL
    assert result["features"]["lighting"] > 0.8
