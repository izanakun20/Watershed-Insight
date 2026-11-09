import os
import sys
import json
import math
import requests
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
import numpy as np
import warnings
warnings.filterwarnings("ignore")

CLIENT_ID = os.getenv("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("COPERNICUS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Missing Credentials for CDSE.")
    sys.exit(1)

print("Authenticating...")
resp = requests.post(
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    data={"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
)
resp.raise_for_status()
TOKEN = resp.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Bounding box & geometry
BBOX = [78.95, 14.90, 80.35, 15.75]  # minX, minY, maxX, maxY
BASIN_PATH = "downloaded_data/bhuvan/gundlakamma_basin_approx.geojson"
with open(BASIN_PATH, "r", encoding="utf-8") as f:
    SHAPES = [feature["geometry"] for feature in json.load(f)["features"]]

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
RES_DEGREES = 10.0 / 111320.0  # 10m in degrees (approx)

def fetch_s2_date(date_range, out_prefix):
    print(f"\n--- Fetching Sentinel-2 for {out_prefix} ({date_range}) ---")
    
    # 1. Search for best date in range
    search_payload = {
        "collections": ["sentinel-2-l2a"],
        "datetime": date_range,
        "bbox": BBOX,
        "limit": 100
    }
    cat_resp = requests.post("https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search", headers=HEADERS, json=search_payload)
    items = cat_resp.json().get("features", [])
    if not items:
        print(f"No items found for {date_range}")
        return None
    
    best_scene = min(items, key=lambda x: x.get("properties", {}).get("eo:cloud_cover", 100))
    day = best_scene["properties"]["datetime"].split("T")[0]
    print(f"Selected Date: {day} (Cloud Cover: {best_scene['properties']['eo:cloud_cover']}%)")

    # 2. Tiling logic for 10m
    width_deg = BBOX[2] - BBOX[0]
    height_deg = BBOX[3] - BBOX[1]
    total_width_px = math.ceil(width_deg / RES_DEGREES)
    total_height_px = math.ceil(height_deg / RES_DEGREES)
    
    CHUNK_SIZE = 2000
    chunks_x = math.ceil(total_width_px / CHUNK_SIZE)
    chunks_y = math.ceil(total_height_px / CHUNK_SIZE)
    
    print(f"Total size: {total_width_px} x {total_height_px} pixels")
    print(f"Tiling into {chunks_x} x {chunks_y} grid ({chunks_x * chunks_y} requests)...")

    os.makedirs("processed_data/temp_tiles", exist_ok=True)
    tiles = []

    for y in range(chunks_y):
        for x in range(chunks_x):
            print(f"  Fetching tile {y*chunks_x + x + 1}/{chunks_x*chunks_y}...")
            
            # Calculate bbox for this chunk
            px_start_x = x * CHUNK_SIZE
            px_start_y = y * CHUNK_SIZE
            px_w = min(CHUNK_SIZE, total_width_px - px_start_x)
            px_h = min(CHUNK_SIZE, total_height_px - px_start_y)
            
            # We want top-down Y, but bbox is minY to maxY (bottom-up)
            # px_start_y=0 means top of the image (maxY).
            # So max_y for this tile is BBOX[3] - (px_start_y * RES_DEGREES)
            # min_y is BBOX[3] - ((px_start_y + px_h) * RES_DEGREES)
            
            c_minx = BBOX[0] + (px_start_x * RES_DEGREES)
            c_maxx = BBOX[0] + ((px_start_x + px_w) * RES_DEGREES)
            
            c_maxy = BBOX[3] - (px_start_y * RES_DEGREES)
            c_miny = BBOX[3] - ((px_start_y + px_h) * RES_DEGREES)
            
            c_bbox = [c_minx, c_miny, c_maxx, c_maxy]
            
            process_payload = {
                "input": {
                    "bounds": {"bbox": c_bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                    "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": {"from": f"{day}T00:00:00Z", "to": f"{day}T23:59:59Z"}}}]
                },
                "output": {"width": px_w, "height": px_h, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
                "evalscript": """
//VERSION=3
function setup() { return { input: ["B03", "B04", "B08", "dataMask"], output: { bands: 4, sampleType: "FLOAT32" } }; }
function evaluatePixel(sample) { return [sample.B03, sample.B04, sample.B08, sample.dataMask]; }
"""
            }
            
            proc_resp = requests.post(PROCESS_URL, headers=HEADERS, json=process_payload)
            if proc_resp.status_code != 200:
                print(f"Error fetching tile: {proc_resp.text}")
                continue
                
            tile_path = f"processed_data/temp_tiles/{out_prefix}_tile_{x}_{y}.tif"
            with open(tile_path, "wb") as f:
                f.write(proc_resp.content)
            tiles.append(tile_path)

    print("Merging tiles...")
    src_files_to_mosaic = []
    for fp in tiles:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)
        
    mosaic, out_trans = merge(src_files_to_mosaic)
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans})
    
    mosaic_path = f"processed_data/raw_bands_{out_prefix}_mosaic.tif"
    with rasterio.open(mosaic_path, "w", **out_meta) as dest:
        dest.write(mosaic)
        
    # Close tiles and cleanup
    for src in src_files_to_mosaic:
        src.close()
    for fp in tiles:
        os.remove(fp)
        
    return mosaic_path

def process_indices(mosaic_path, year):
    print(f"Processing indices for {year}...")
    with rasterio.open(mosaic_path) as src:
        out_image, out_transform = mask(src, SHAPES, crop=True)
        out_meta = src.meta.copy()

    green = out_image[0]
    red = out_image[1]
    nir = out_image[2]
    data_mask = out_image[3]

    np.seterr(divide='ignore', invalid='ignore')
    
    ndvi = np.where((nir + red) == 0., 0, (nir - red) / (nir + red))
    ndvi = np.where(data_mask == 0, np.nan, ndvi)
    
    ndwi = np.where((green + nir) == 0., 0, (green - nir) / (green + nir))
    ndwi = np.where(data_mask == 0, np.nan, ndwi)
    
    water = np.where(ndwi > 0.1, 1, 0).astype(rasterio.uint8)
    water = np.where(data_mask == 0, 0, water)
    
    out_meta.update({
        "count": 1,
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": np.nan
    })
    
    suffix = "clipped" if year == "2026" else year
    
    with rasterio.open(f"processed_data/ndvi_{suffix}.tif", "w", **out_meta) as dest:
        dest.write(ndvi.astype(rasterio.float32), 1)
        
    with rasterio.open(f"processed_data/ndwi_{suffix}.tif", "w", **out_meta) as dest:
        dest.write(ndwi.astype(rasterio.float32), 1)
        
    out_meta_mask = out_meta.copy()
    out_meta_mask.update({"dtype": "uint8", "nodata": 0})
    with rasterio.open(f"processed_data/water_mask_{suffix}.tif", "w", **out_meta_mask) as dest:
        dest.write(water, 1)

    return f"processed_data/ndvi_{suffix}.tif", f"processed_data/ndwi_{suffix}.tif", f"processed_data/water_mask_{suffix}.tif"

def calculate_changes():
    print("\n--- Calculating Change Layers (2026 - 2025) ---")
    with rasterio.open("processed_data/ndvi_clipped.tif") as src:
        ndvi_26 = src.read(1)
        meta = src.meta.copy()
    with rasterio.open("processed_data/ndvi_2025.tif") as src:
        ndvi_25 = src.read(1)
        
    with rasterio.open("processed_data/ndwi_clipped.tif") as src:
        ndwi_26 = src.read(1)
    with rasterio.open("processed_data/ndwi_2025.tif") as src:
        ndwi_25 = src.read(1)
        
    with rasterio.open("processed_data/water_mask_clipped.tif") as src:
        water_26 = src.read(1)
    with rasterio.open("processed_data/water_mask_2025.tif") as src:
        water_25 = src.read(1)

    # They should match exactly because they use the same bbox, resolution, and clip geometry.
    if ndvi_25.shape != ndvi_26.shape:
        print("Shape mismatch. Cannot compute change.")
        return

    ndvi_change = ndvi_26 - ndvi_25
    ndwi_change = ndwi_26 - ndwi_25
    water_change = water_26.astype(np.int16) - water_25.astype(np.int16)

    with rasterio.open("processed_data/ndvi_change_2025_2026.tif", "w", **meta) as dest:
        dest.write(ndvi_change.astype(rasterio.float32), 1)
        
    with rasterio.open("processed_data/ndwi_change_2025_2026.tif", "w", **meta) as dest:
        dest.write(ndwi_change.astype(rasterio.float32), 1)
        
    meta_change_water = meta.copy()
    meta_change_water.update({"dtype": "int16", "nodata": -9999})
    water_change_out = np.where(np.isnan(ndvi_change), -9999, water_change)
    with rasterio.open("processed_data/water_change_2025_2026.tif", "w", **meta_change_water) as dest:
        dest.write(water_change_out.astype(np.int16), 1)
        
    print("Change layers generated.")

def main():
    # 2025
    mos_2025 = fetch_s2_date("2025-07-01T00:00:00Z/2025-07-31T23:59:59Z", "2025")
    if mos_2025:
        process_indices(mos_2025, "2025")

    # 2026
    mos_2026 = fetch_s2_date("2026-07-01T00:00:00Z/2026-07-31T23:59:59Z", "2026")
    if mos_2026:
        process_indices(mos_2026, "2026")
        
    if mos_2025 and mos_2026:
        calculate_changes()
        
    print("\nDone. 10m native resolution processing complete.")

if __name__ == "__main__":
    main()
