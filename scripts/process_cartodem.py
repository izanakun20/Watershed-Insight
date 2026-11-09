import os
import sys
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
import geopandas as gpd
from pysheds.grid import Grid
import json
import glob

print("=======================================")
print("CartoDEM 30m Processing Script (Mosaic)")
print("=======================================")

# Look for all CartoDEM files
search_pattern = "downloaded_data/*cartodem*.tif"
candidates = [f for f in glob.glob(search_pattern) if "clipped" not in f]

if not candidates:
    print(f"Error: Could not find any CartoDEM files matching {search_pattern}.")
    sys.exit(1)

print(f"Found {len(candidates)} CartoDEM tiles. Mosaicing them...")

# 1. Mosaic the tiles
src_files_to_mosaic = []
for fp in candidates:
    src_files_to_mosaic.append(rasterio.open(fp))

mosaic, out_trans = merge(src_files_to_mosaic)
out_meta = src_files_to_mosaic[0].meta.copy()

out_meta.update({
    "driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_trans
})

mosaic_path = "processed_data/cartodem_mosaic.tif"
with rasterio.open(mosaic_path, "w", **out_meta) as dest:
    dest.write(mosaic)

for src in src_files_to_mosaic:
    src.close()

print(f"Saved mosaiced DEM to: {mosaic_path}")

# Load AOI boundary
basin_path = "downloaded_data/bhuvan/gundlakamma_basin_approx.geojson"
with open(basin_path, "r", encoding="utf-8") as f:
    shapes = [feature["geometry"] for feature in json.load(f)["features"]]

# 2. Clip Mosaic to AOI
print("\nClipping Mosaiced DEM to Gundlakamma AOI...")
clipped_dem_path = "processed_data/cartodem_clipped.tif"

with rasterio.open(mosaic_path) as src:
    out_image, out_transform = mask(src, shapes, crop=True)
    out_meta = src.meta.copy()
    
    # Original CartoDEM NoData might be -32768.0
    original_nodata = src.nodata if src.nodata is not None else -32768.0

out_meta.update({
    "count": 1,
    "height": out_image.shape[1],
    "width": out_image.shape[2],
    "transform": out_transform,
    "nodata": -9999
})

# Replace the original nodata with -9999
clipped_array = np.where(out_image[0] == original_nodata, -9999, out_image[0])
# Also replace any existing -9999 or nan
clipped_array = np.where(np.isnan(clipped_array), -9999, clipped_array)

with rasterio.open(clipped_dem_path, "w", **out_meta) as dest:
    dest.write(clipped_array.astype(rasterio.float32), 1)

print(f"Saved clipped DEM to: {clipped_dem_path}")

# Check valid pixels
valid_pixels = (clipped_array != -9999).sum()
print(f"Valid pixels after clipping: {valid_pixels}")

if valid_pixels == 0:
    print("ERROR: No valid pixels in the clipped DEM. The downloaded tiles do not cover the AOI.")
    sys.exit(1)

# 3. Pysheds Hydrological Processing
print("\nInitializing Pysheds grid...")
grid = Grid.from_raster(clipped_dem_path)
dem = grid.read_raster(clipped_dem_path)

print("Filling depressions (Sink Fill)...")
filled_dem = grid.fill_depressions(dem)

print("Resolving flats...")
resolved_dem = grid.resolve_flats(filled_dem)

print("Calculating D8 flow direction...")
fdir = grid.flowdir(resolved_dem)

print("Calculating flow accumulation...")
acc = grid.accumulation(fdir)

# 4. Extract Drainage Network
print("\nExtracting stream network (threshold > 1000 pixels)...")
stream_mask = acc > 1000 

print("Vectorizing streams to GeoJSON...")
branches = grid.extract_river_network(fdir, stream_mask)

features = []
with rasterio.open(clipped_dem_path) as src:
    crs = src.crs

if branches and 'features' in branches:
    for i, branch in enumerate(branches['features']):
        features.append({
            'geometry': branch['geometry'],
            'properties': {'id': i}
        })

    gdf = gpd.GeoDataFrame.from_features(features, crs=crs)
    drainage_path = "processed_data/cartodem_drainage.geojson"
    gdf.to_file(drainage_path, driver="GeoJSON")
    print(f"Drainage network saved to: {drainage_path}")
else:
    print("No stream network could be extracted (perhaps no rivers met the threshold).")

# 5. Calculate Slope
print("\nCalculating Slope...")
with rasterio.open(clipped_dem_path) as src:
    elev = src.read(1)
    transform = src.transform
    out_meta_slope = src.meta.copy()

# Cell sizes in meters (approximate for EPSG:4326 at this latitude)
dx = 107000 * transform.a
dy = 111000 * abs(transform.e)

px, py = np.gradient(elev, dx, dy)
slope = np.sqrt(px**2 + py**2)
slope_deg = np.degrees(np.arctan(slope))

# Mask out nodata
slope_deg = np.where(elev == -9999, -9999, slope_deg)

slope_path = "processed_data/cartodem_slope.tif"
with rasterio.open(slope_path, "w", **out_meta_slope) as dest:
    dest.write(slope_deg.astype(rasterio.float32), 1)

print(f"Slope raster saved to: {slope_path}")
print("\nSUCCESS: All CartoDEM layers generated successfully!")
