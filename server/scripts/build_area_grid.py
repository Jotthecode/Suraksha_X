"""
Build the bundled lighting / activity grid (server/data/india_area_grid.npz) from an
OpenStreetMap extract, so area risk and safe routes don't depend on the public Overpass API.

    pip install osmium
    # India extract, ~1.7 GB: https://download.geofabrik.de/asia/india-latest.osm.pbf
    python scripts/build_area_grid.py path/to/india-latest.osm.pbf

What it counts (same inputs the live Overpass query used, see services/geo.py):
  - lamps:    nodes tagged highway=street_lamp
  - activity: nodes tagged shop=* or amenity=*
per cell of a 0.001° x 0.001° grid (~110 m x ~105 m in India). Only non-empty cells are stored.
"""

import sys
import time
from pathlib import Path

import numpy as np
import osmium

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.area_grid import CELL_DEG, COLS, LAT0, LON0, ROWS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "india_area_grid.npz"


def main(pbf_path: str):
    t0 = time.time()
    lamp_keys, act_keys = [], []
    seen = 0

    processor = (
        osmium.FileProcessor(pbf_path)
        .with_filter(osmium.filter.EntityFilter(osmium.osm.NODE))
        .with_filter(osmium.filter.KeyFilter("highway", "shop", "amenity"))
    )
    for node in processor:
        seen += 1
        loc = node.location
        if not loc.valid():
            continue
        row = int((loc.lat - LAT0) / CELL_DEG)
        col = int((loc.lon - LON0) / CELL_DEG)
        if not (0 <= row < ROWS and 0 <= col < COLS):
            continue
        key = row * COLS + col
        tags = node.tags
        if tags.get("highway") == "street_lamp":
            lamp_keys.append(key)
        if "shop" in tags or "amenity" in tags:
            act_keys.append(key)
        if seen % 2_000_000 == 0:
            print(f"  {seen:,} tagged nodes, {len(lamp_keys):,} lamps, {len(act_keys):,} activity  ({time.time() - t0:.0f} s)")

    lamp_keys = np.asarray(lamp_keys, dtype=np.int64)
    act_keys = np.asarray(act_keys, dtype=np.int64)
    keys = np.union1d(lamp_keys, act_keys)

    def counts_for(src):
        uniq, cnt = np.unique(src, return_counts=True)
        out = np.zeros(len(keys), dtype=np.uint16)
        out[np.searchsorted(keys, uniq)] = np.minimum(cnt, 65535)
        return out

    np.savez_compressed(
        OUT,
        keys=keys.astype(np.int32),
        lamps=counts_for(lamp_keys),
        activity=counts_for(act_keys),
        meta=np.array([LAT0, LON0, CELL_DEG, ROWS, COLS]),
        source=np.array([Path(pbf_path).name]),
    )
    print(
        f"Done in {time.time() - t0:.0f} s: {len(lamp_keys):,} lamps, {len(act_keys):,} shops/amenities, "
        f"{len(keys):,} cells -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/build_area_grid.py <india.osm.pbf>")
    main(sys.argv[1])
