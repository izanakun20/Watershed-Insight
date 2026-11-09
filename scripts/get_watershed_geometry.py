"""
Prakasam Watershed Geometry Builder
====================================
Downloads and saves:
  1. Prakasam district boundary (from GADM via GitHub)
  2. Gundlakamma basin approximate polygon
  3. OpenStreetMap query for Gundlakamma river
  4. Sentinel-2 tile index for AP

Run:
    python scripts/get_watershed_geometry.py
"""

import os
import sys
import json
import time
import requests

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "downloaded_data", "bhuvan")
os.makedirs(OUT_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "SIH26015-GeometryBuilder/1.0"

TIMEOUT = 60

def save_json(data, filename: str):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")
    return path


# ─── 1. Prakasam district via Nominatim ──────────────────────────────────────
print("\n[1] Querying Nominatim for Prakasam district boundary...")
try:
    r = SESSION.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q":              "Prakasam district Andhra Pradesh India",
            "format":         "geojson",
            "polygon_geojson": 1,
            "limit":          3,
            "addressdetails": 1,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    print(f"  → {len(data.get('features', []))} features returned")
    # Pick the administrative boundary (admin_level=5 or 6)
    features = data.get("features", [])
    for feat in features:
        print(f"    - {feat['properties'].get('display_name', '')[:80]}")
    if features:
        save_json(data, "prakasam_nominatim.geojson")
except Exception as e:
    print(f"  ERROR: {e}")

time.sleep(1)

# ─── 2. Overpass API — Gundlakamma river ────────────────────────────────────
print("\n[2] Querying Overpass API for Gundlakamma river...")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
overpass_query = """
[out:json][timeout:30];
(
  relation["name"~"Gundlakamma", i]["waterway"];
  way["name"~"Gundlakamma", i]["waterway"];
  relation["name"~"Prakasam"]["boundary"="administrative"];
);
out body geom;
"""
try:
    r = SESSION.post(OVERPASS_URL, data=overpass_query, timeout=60)
    r.raise_for_status()
    data = r.json()
    elements = data.get("elements", [])
    print(f"  → {len(elements)} OSM elements returned")
    for el in elements[:5]:
        tags = el.get("tags", {})
        print(f"    - type={el.get('type')} name={tags.get('name','')} waterway={tags.get('waterway','')}")
    if elements:
        save_json(data, "gundlakamma_overpass.json")
except Exception as e:
    print(f"  ERROR: {e}")

time.sleep(1)

# ─── 3. Definitive GeoJSON polygon for Gundlakamma basin ────────────────────
# Based on known geographic facts:
# Gundlakamma river originates near Nallamala hills, flows ~256 km,
# drains into Bay of Bengal near Chirala. Basin covers ~7,000 km².
print("\n[3] Saving Gundlakamma watershed approximate polygon (hand-crafted)...")
gundlakamma_geojson = {
    "type": "FeatureCollection",
    "name": "Gundlakamma_Watershed_Prakasam_AP",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": [
        {
            "type": "Feature",
            "id": "gundlakamma_basin",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    # Approximate boundary of Gundlakamma basin
                    # Western: Nallamala hills origin
                    # Eastern: Bay of Bengal near Chirala/Vetapalem
                    # Northern: ~15.7°N
                    # Southern: ~15.2°N
                    [78.95, 15.25],
                    [79.25, 15.10],
                    [79.50, 14.95],
                    [79.75, 14.90],
                    [80.00, 14.95],
                    [80.20, 15.10],
                    [80.35, 15.35],  # Bay of Bengal mouth (Chirala coast)
                    [80.25, 15.60],
                    [80.00, 15.70],
                    [79.70, 15.75],
                    [79.40, 15.65],
                    [79.10, 15.50],
                    [78.95, 15.35],
                    [78.95, 15.25],
                ]],
            },
            "properties": {
                "name": "Gundlakamma River Basin",
                "district": "Prakasam",
                "state": "Andhra Pradesh",
                "approx_area_km2": 7000,
                "river_length_km": 256,
                "origin": "Nallamala hills near Allagadda",
                "outfall": "Bay of Bengal near Chirala",
                "notes": "Approximate polygon — refine with India-WRIS/Bhuvan Watershed Atlas",
                "centroid_lon": 79.65,
                "centroid_lat": 15.35,
            },
        }
    ],
}
save_json(gundlakamma_geojson, "gundlakamma_basin_approx.geojson")

# Also save bounding box for WMS/API queries
bbox_info = {
    "name": "Gundlakamma_Basin_BBOX",
    "minLon": 78.95,
    "minLat": 14.90,
    "maxLon": 80.35,
    "maxLat": 15.75,
    "centroid": {"lon": 79.65, "lat": 15.33},
    "sentinel2_tiles": ["44QNG", "44QNF", "44QMG"],  # MGRS tiles over this area
    "landsat_wrs2": "path=140,141 row=051,052",
    "notes": "Use India-WRIS for official watershed boundary",
}
save_json(bbox_info, "aoi_bbox.json")
print(f"  → BBOX: {bbox_info['minLon']},{bbox_info['minLat']} to {bbox_info['maxLon']},{bbox_info['maxLat']}")

# ─── 4. Query Bhuvan WMS for available LULC layers ──────────────────────────
print("\n[4] Testing Bhuvan WMS GetCapabilities...")
try:
    r = SESSION.get(
        "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
        params={"service": "WMS", "version": "1.1.1", "request": "GetCapabilities"},
        timeout=30,
    )
    print(f"  → HTTP {r.status_code}, Content-Type: {r.headers.get('Content-Type','')}, Size: {len(r.content)} bytes")
    if r.status_code == 200:
        # Extract layer names from XML
        import re
        layers = re.findall(r"<Name>(.*?)</Name>", r.text)
        relevant = [l for l in layers if any(k in l.lower() for k in
                    ["lulc","watershed","drain","soil","water","ndvi","dem","prakasam","ap_"])]
        print(f"  → Total layers in WMS: {len(layers)}")
        print(f"  → Potentially relevant layers: {len(relevant)}")
        for l in relevant[:20]:
            print(f"    - {l}")
        # Save full capabilities
        cap_path = os.path.join(OUT_DIR, "bhuvan_wms_capabilities.xml")
        with open(cap_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"  → Saved WMS capabilities to: {cap_path}")
        save_json({"all_layers": layers, "relevant_layers": relevant}, "bhuvan_wms_layers.json")
    else:
        print(f"  → Failed: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─── 5. Try Bhuvan WMS GetMap for our AOI ───────────────────────────────────
print("\n[5] Testing Bhuvan WMS GetMap for Prakasam LULC 50K 2015-16...")
try:
    r = SESSION.get(
        "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
        params={
            "service":     "WMS",
            "version":     "1.1.1",
            "request":     "GetMap",
            "layers":      "bhuvan:BR_LULC50K_1516",
            "bbox":        "78.95,14.90,80.35,15.75",
            "width":       "512",
            "height":      "512",
            "srs":         "EPSG:4326",
            "format":      "image/png",
            "transparent": "TRUE",
        },
        timeout=30,
    )
    print(f"  → HTTP {r.status_code}, Content-Type: {r.headers.get('Content-Type','')}")
    if r.status_code == 200 and "image" in r.headers.get("Content-Type",""):
        img_path = os.path.join(OUT_DIR, "lulc50k_1516_prakasam_wms.png")
        with open(img_path, "wb") as f:
            f.write(r.content)
        print(f"  ✅ Saved WMS tile: {img_path} ({len(r.content)} bytes)")
    elif r.status_code == 200:
        print(f"  → Unexpected content type. Preview: {r.text[:300]}")
    else:
        print(f"  → Error: {r.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─── 6. Try other key WMS layers ────────────────────────────────────────────
wms_layers_to_try = [
    ("bhuvan:BR_LULC50K_1112", "lulc50k_1112_prakasam_wms.png", "LULC 50K 2011-12"),
    ("bhuvan:BR_LULC50K_0506", "lulc50k_0506_prakasam_wms.png", "LULC 50K 2005-06"),
    ("bhuvan:india_watershed",  "watershed_prakasam_wms.png",    "Watershed boundaries"),
    ("bhuvan:india_drain",      "drainage_prakasam_wms.png",     "Drainage network"),
    ("bhuvan:water_bodies_india","waterbodies_prakasam_wms.png", "Water bodies"),
]

for layer_name, filename, label in wms_layers_to_try:
    print(f"\n[WMS] {label} ({layer_name})")
    try:
        r = SESSION.get(
            "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
            params={
                "service": "WMS", "version": "1.1.1", "request": "GetMap",
                "layers": layer_name,
                "bbox": "78.95,14.90,80.35,15.75",
                "width": "512", "height": "512",
                "srs": "EPSG:4326",
                "format": "image/png", "transparent": "TRUE",
            },
            timeout=30,
        )
        print(f"  → HTTP {r.status_code}, CT: {r.headers.get('Content-Type','')} ({len(r.content)} bytes)")
        if r.status_code == 200 and "image" in r.headers.get("Content-Type",""):
            img_path = os.path.join(OUT_DIR, filename)
            with open(img_path, "wb") as f:
                f.write(r.content)
            print(f"  ✅ Saved: {img_path}")
        time.sleep(0.5)
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n\nGeometry setup complete. Check downloaded_data/bhuvan/")
