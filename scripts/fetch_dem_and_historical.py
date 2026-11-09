import os
import sys
import json
import requests
import rasterio
from rasterio.mask import mask
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# 1. Credentials
CLIENT_ID = os.getenv("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("COPERNICUS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Missing Credentials.")
    sys.exit(1)

# 2. Auth
print("Authenticating...")
resp = requests.post(
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    data={"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
)
resp.raise_for_status()
TOKEN = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {TOKEN}"}

# Bounding box & geometry
bbox = [78.95, 14.90, 80.35, 15.75]
width, height = 1400, 850
basin_path = "downloaded_data/bhuvan/gundlakamma_basin_approx.geojson"
with open(basin_path, "r", encoding="utf-8") as f:
    shapes = [feature["geometry"] for feature in json.load(f)["features"]]

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# ---------------------------------------------------------
# TASK 1: FETCH DEM
# ---------------------------------------------------------
print("\n--- Fetching Copernicus GLO-30 DEM ---")
dem_payload = {
    "input": {
        "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
        "data": [{"type": "dem", "dataFilter": {"demInstance": "COPERNICUS_30"}}]
    },
    "output": {"width": width, "height": height, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
    "evalscript": """
//VERSION=3
function setup() { return { input: ["DEM"], output: { bands: 1, sampleType: "FLOAT32" } }; }
function evaluatePixel(sample) { return [sample.DEM]; }
"""
}

dem_resp = requests.post(PROCESS_URL, headers=headers, json=dem_payload)
if dem_resp.status_code != 200:
    print("Failed to fetch DEM:", dem_resp.text)
else:
    raw_dem_path = "processed_data/raw_dem.tif"
    with open(raw_dem_path, "wb") as f:
        f.write(dem_resp.content)
    
    # Clip DEM
    with rasterio.open(raw_dem_path) as src:
        out_image, out_transform = mask(src, shapes, crop=True)
        out_meta = src.meta.copy()
        
    out_meta.update({"count": 1, "height": out_image.shape[1], "width": out_image.shape[2], "transform": out_transform, "nodata": np.nan})
    dem_clipped = np.where(out_image[0] == src.nodata, np.nan, out_image[0])
    
    dem_path = "processed_data/dem_clipped.tif"
    with rasterio.open(dem_path, "w", **out_meta) as dest:
        dest.write(dem_clipped.astype(rasterio.float32), 1)
    print(f"DEM saved to {dem_path}")

# ---------------------------------------------------------
# TASK 2: HISTORICAL SENTINEL-2 (July 2025)
# ---------------------------------------------------------
print("\n--- Fetching Historical Sentinel-2 (July 2025) ---")
search_payload = {
    "collections": ["sentinel-2-l2a"],
    "datetime": "2025-07-01T00:00:00Z/2025-07-31T23:59:59Z",
    "bbox": bbox,
    "limit": 100
}
cat_resp = requests.post("https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search", headers=headers, json=search_payload)
items = cat_resp.json().get("features", [])
best_scene = min(items, key=lambda x: x.get("properties", {}).get("eo:cloud_cover", 100))
day = best_scene["properties"]["datetime"].split("T")[0]
print(f"Selected 2025 Scene Date: {day} (Cloud Cover: {best_scene['properties']['eo:cloud_cover']}%)")

process_payload = {
    "input": {
        "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
        "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": {"from": f"{day}T00:00:00Z", "to": f"{day}T23:59:59Z"}}}]
    },
    "output": {"width": width, "height": height, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
    "evalscript": """
//VERSION=3
function setup() { return { input: ["B03", "B04", "B08", "dataMask"], output: { bands: 4, sampleType: "FLOAT32" } }; }
function evaluatePixel(sample) { return [sample.B03, sample.B04, sample.B08, sample.dataMask]; }
"""
}

proc_resp = requests.post(PROCESS_URL, headers=headers, json=process_payload)
proc_resp.raise_for_status()

raw_tif_2025 = "processed_data/raw_bands_2025.tif"
with open(raw_tif_2025, "wb") as f:
    f.write(proc_resp.content)

# Clip and Calculate Indices for 2025
with rasterio.open(raw_tif_2025) as src:
    out_image_25, out_transform_25 = mask(src, shapes, crop=True)
    out_meta_25 = src.meta.copy()

green_25 = out_image_25[0]
red_25 = out_image_25[1]
nir_25 = out_image_25[2]
mask_25 = out_image_25[3]

np.seterr(divide='ignore', invalid='ignore')
ndvi_25 = np.where((nir_25 + red_25) == 0., 0, (nir_25 - red_25) / (nir_25 + red_25))
ndvi_25 = np.where(mask_25 == 0, np.nan, ndvi_25)

ndwi_25 = np.where((green_25 + nir_25) == 0., 0, (green_25 - nir_25) / (green_25 + nir_25))
ndwi_25 = np.where(mask_25 == 0, np.nan, ndwi_25)

water_25 = np.where(ndwi_25 > 0.1, 1, 0).astype(rasterio.uint8)
water_25 = np.where(mask_25 == 0, 0, water_25)

out_meta_25.update({"count": 1, "height": out_image_25.shape[1], "width": out_image_25.shape[2], "transform": out_transform_25, "nodata": np.nan})

with rasterio.open("processed_data/ndvi_2025.tif", "w", **out_meta_25) as dest:
    dest.write(ndvi_25.astype(rasterio.float32), 1)

with rasterio.open("processed_data/ndwi_2025.tif", "w", **out_meta_25) as dest:
    dest.write(ndwi_25.astype(rasterio.float32), 1)

out_meta_mask = out_meta_25.copy()
out_meta_mask.update({"dtype": "uint8", "nodata": 0})
with rasterio.open("processed_data/water_mask_2025.tif", "w", **out_meta_mask) as dest:
    dest.write(water_25, 1)

print("Saved 2025 indices.")

# ---------------------------------------------------------
# TASK 3: CHANGE DETECTION (2026 - 2025)
# ---------------------------------------------------------
print("\n--- Calculating Change Layers ---")
# Load 2026 indices
with rasterio.open("processed_data/ndvi_clipped.tif") as src:
    ndvi_26 = src.read(1)
with rasterio.open("processed_data/ndwi_clipped.tif") as src:
    ndwi_26 = src.read(1)
with rasterio.open("processed_data/water_mask_clipped.tif") as src:
    water_26 = src.read(1)

# Ensure shapes match (they should since we used same bounds, width, height, and clip geometry)
if ndvi_25.shape == ndvi_26.shape:
    ndvi_change = ndvi_26 - ndvi_25
    ndwi_change = ndwi_26 - ndwi_25
    water_change = water_26.astype(np.int16) - water_25.astype(np.int16) # -1: lost water, 0: no change, 1: gained water
    
    with rasterio.open("processed_data/ndvi_change_2025_2026.tif", "w", **out_meta_25) as dest:
        dest.write(ndvi_change.astype(rasterio.float32), 1)
        
    with rasterio.open("processed_data/ndwi_change_2025_2026.tif", "w", **out_meta_25) as dest:
        dest.write(ndwi_change.astype(rasterio.float32), 1)
        
    out_meta_change_water = out_meta_25.copy()
    out_meta_change_water.update({"dtype": "int16", "nodata": -9999})
    # Fill nan areas with nodata for water change
    water_change_out = np.where(np.isnan(ndvi_change), -9999, water_change)
    with rasterio.open("processed_data/water_change_2025_2026.tif", "w", **out_meta_change_water) as dest:
        dest.write(water_change_out.astype(np.int16), 1)
        
    print("Change layers successfully generated (2026 minus 2025).")
else:
    print(f"Shape mismatch! 2025: {ndvi_25.shape}, 2026: {ndvi_26.shape}. Cannot compute change layers directly.")
