import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape
from pysheds.grid import Grid
import os

print("Loading clipped DEM...")
dem_path = "processed_data/dem_clipped.tif"

if not os.path.exists(dem_path):
    print(f"Error: {dem_path} not found.")
    exit(1)

# Initialize grid from raster
grid = Grid.from_raster(dem_path)
dem = grid.read_raster(dem_path)

# Ensure no nan/nodata issues for routing
nodata = dem.nodata if hasattr(dem, 'nodata') and dem.nodata is not None else np.nan
if np.isnan(nodata):
    dem_array = np.where(np.isnan(dem), -9999, dem)
    grid.nodata = -9999
else:
    dem_array = dem

print("Filling depressions (Sink Fill)...")
filled_dem = grid.fill_depressions(dem_array)

print("Resolving flats...")
resolved_dem = grid.resolve_flats(filled_dem)

print("Calculating D8 flow direction...")
# D8 routing
fdir = grid.flowdir(resolved_dem)

print("Calculating flow accumulation...")
acc = grid.accumulation(fdir)

# ---------------------------------------------------------
# Extract Drainage Network
# ---------------------------------------------------------
print("Extracting stream network (threshold > 100 pixels)...")
# Threshold depends on resolution. 1400x850 for 150kmx90km means ~100m per pixel.
# 100 pixels = 100 * 100m * 100m = 1 sq km accumulation threshold
stream_mask = acc > 100

# Vectorize the stream mask
with rasterio.open(dem_path) as src:
    transform = src.transform
    crs = src.crs

# Generate LineStrings
# Since stream_mask is binary, we can convert to polygon features, but for lines we ideally trace.
# A simpler way to save the network is to vectorize the mask as polygons and keep the '1's.
# A true line network requires tracing, which pysheds can do via `extract_river_network`
print("Vectorizing streams to GeoJSON...")
branches = grid.extract_river_network(fdir, stream_mask)

# `branches` is a geojson-like dict with LineStrings
schema = {'geometry': 'LineString', 'properties': {'id': 'int'}}
features = []
for i, branch in enumerate(branches['features']):
    features.append({
        'geometry': branch['geometry'],
        'properties': {'id': i}
    })

gdf = gpd.GeoDataFrame.from_features(features, crs=crs)
drainage_path = "processed_data/drainage_network.geojson"
gdf.to_file(drainage_path, driver="GeoJSON")
print(f"Drainage network saved to {drainage_path}")


# ---------------------------------------------------------
# Calculate Slope
# ---------------------------------------------------------
print("Calculating Slope...")
# Using a simple gradient method. Cell size is roughly 0.001 degrees (~100m).
with rasterio.open(dem_path) as src:
    elev = src.read(1)
    out_meta = src.meta.copy()

# Cell sizes in meters (approximate for EPSG:4326 at this latitude)
# 1 degree lat ~ 111km. 1 degree lon ~ 111km * cos(15 deg) ~ 107km.
dx = 107000 * transform.a
dy = 111000 * abs(transform.e)

px, py = np.gradient(elev, dx, dy)
slope = np.sqrt(px**2 + py**2)
# Convert to degrees
slope_deg = np.degrees(np.arctan(slope))
# Restore nodata
slope_deg = np.where(elev == nodata, np.nan, slope_deg)
slope_deg = np.where(np.isnan(elev), np.nan, slope_deg)

slope_path = "processed_data/slope.tif"
with rasterio.open(slope_path, "w", **out_meta) as dest:
    dest.write(slope_deg.astype(rasterio.float32), 1)

print(f"Slope raster saved to {slope_path}")
print("Drainage and Slope generation complete!")
