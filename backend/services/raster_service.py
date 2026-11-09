"""
Raster Service - Centralized raster I/O for SIH 26015
Handles all GeoTIFF operations: sampling, zonal stats, hotspot detection.
"""
import os
import math
import json
import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import shape, Point, mapping

# Base directory (relative to where uvicorn is launched from)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED_DIR = os.path.join(BASE_DIR, "processed_data")
BASIN_PATH = os.path.join(BASE_DIR, "downloaded_data", "bhuvan", "gundlakamma_basin_approx.geojson")


class RasterService:
    """Manages all raster data access for the watershed application."""

    def __init__(self):
        self.watershed_shape = None
        self.watershed_geojson = None
        self.rasters = {}
        self._stats_cache = None
        self._hotspots_cache = None

    def load(self):
        """Load watershed boundary and open all raster files."""
        # Load watershed boundary
        if os.path.exists(BASIN_PATH):
            with open(BASIN_PATH, "r", encoding="utf-8") as f:
                self.watershed_geojson = json.load(f)
                self.watershed_shape = shape(self.watershed_geojson["features"][0]["geometry"])

        # Open rasters
        raster_files = {
            "ndvi_current": "ndvi_clipped.tif",
            "ndvi_2025": "ndvi_2025.tif",
            "ndvi_change": "ndvi_change_2025_2026.tif",
            "ndwi_current": "ndwi_clipped.tif",
            "ndwi_2025": "ndwi_2025.tif",
            "ndwi_change": "ndwi_change_2025_2026.tif",
            "water_current": "water_mask_clipped.tif",
            "water_2025": "water_mask_2025.tif",
            "water_change": "water_change_2025_2026.tif",
        }

        for key, filename in raster_files.items():
            path = os.path.join(PROCESSED_DIR, filename)
            if os.path.exists(path):
                try:
                    self.rasters[key] = rasterio.open(path)
                    print(f"  Loaded raster: {key} ({filename})")
                except Exception as e:
                    print(f"  Warning: Could not open {filename}: {e}")

    def close(self):
        """Close all open raster files."""
        for key, src in self.rasters.items():
            try:
                src.close()
            except Exception:
                pass

    def is_inside_watershed(self, lat: float, lon: float) -> bool:
        """Check if a point falls inside the watershed boundary."""
        if not self.watershed_shape:
            return False
        return self.watershed_shape.contains(Point(lon, lat))

    def sample_point(self, lat: float, lon: float) -> dict:
        """Sample all rasters at a given point. Returns dict of values."""
        coords = [(lon, lat)]
        result = {}

        for key, src in self.rasters.items():
            try:
                gen = src.sample(coords)
                val = float(next(gen)[0])
                if math.isnan(val):
                    val = None
                result[key] = val
            except Exception:
                result[key] = None

        return result

    def compute_zonal_stats(self) -> dict:
        """Compute zonal statistics within the watershed polygon.
        Results are cached after first computation.
        """
        if self._stats_cache is not None:
            return self._stats_cache

        if not self.watershed_shape or not self.watershed_geojson:
            return {}

        stats = {}
        geom = [self.watershed_geojson["features"][0]["geometry"]]

        for key in ["ndvi_current", "ndwi_current", "water_current", "ndvi_change", "ndwi_change", "water_change"]:
            if key not in self.rasters:
                continue

            src = self.rasters[key]
            try:
                is_integer = np.issubdtype(src.dtypes[0], np.integer)
                
                if is_integer:
                    # For integer rasters (water mask/change), the source nodata=0
                    # conflicts with valid values. Read raw data and mask by polygon.
                    from rasterio.features import geometry_mask
                    raw_data = src.read(1).astype(np.float32)
                    # Create a mask: True where OUTSIDE the polygon
                    poly_mask = geometry_mask(
                        [shape(geom[0])], 
                        out_shape=src.shape, 
                        transform=src.transform,
                        invert=False  # True=outside polygon
                    )
                    raw_data[poly_mask] = np.nan
                    valid = raw_data[~np.isnan(raw_data)]
                else:
                    out_image, out_transform = rio_mask(src, geom, crop=True, nodata=np.nan)
                    data = out_image[0]
                    valid = data[~np.isnan(data)]

                if len(valid) == 0:
                    continue

                stat = {
                    "mean": round(float(np.mean(valid)), 4),
                    "median": round(float(np.median(valid)), 4),
                    "std": round(float(np.std(valid)), 4),
                    "min": round(float(np.min(valid)), 4),
                    "max": round(float(np.max(valid)), 4),
                    "valid_pixels": int(len(valid)),
                }

                # Additional category stats for specific layers
                if key == "ndvi_current":
                    stat["high_veg_pct"] = round(100.0 * np.sum(valid > 0.4) / len(valid), 1)
                    stat["low_veg_pct"] = round(100.0 * np.sum(valid < 0.2) / len(valid), 1)
                    stat["moderate_veg_pct"] = round(100.0 * np.sum((valid >= 0.2) & (valid <= 0.4)) / len(valid), 1)

                if key == "water_current":
                    total_valid = len(valid)
                    water_pixels = int(np.sum(valid == 1))
                    stat["water_area_pct"] = round(100.0 * water_pixels / total_valid, 2) if total_valid > 0 else 0
                    # Approximate area: each pixel is ~111m x 111m at this resolution
                    pixel_area_ha = (111 * 111) / 10000  # hectares per pixel
                    stat["water_area_ha"] = round(water_pixels * pixel_area_ha, 1)

                if key == "ndvi_change":
                    stat["improved_pct"] = round(100.0 * np.sum(valid > 0.05) / len(valid), 1)
                    stat["degraded_pct"] = round(100.0 * np.sum(valid < -0.05) / len(valid), 1)
                    stat["stable_pct"] = round(100.0 * np.sum(np.abs(valid) <= 0.05) / len(valid), 1)

                stats[key] = stat

            except Exception as e:
                print(f"  Warning: Zonal stats failed for {key}: {e}")

        self._stats_cache = stats
        return stats

    def get_hotspots(self, layer_key: str = "ndvi_change", top_n: int = 10) -> list:
        """Find locations with the largest absolute change values.
        Returns list of {lat, lon, value, type} dicts.
        """
        cache_key = f"{layer_key}_{top_n}"
        if self._hotspots_cache and cache_key in self._hotspots_cache:
            return self._hotspots_cache[cache_key]

        if layer_key not in self.rasters:
            return []

        src = self.rasters[layer_key]
        data = src.read(1)

        # Mask NaN
        valid_mask = ~np.isnan(data)
        if src.nodata is not None and not np.isnan(src.nodata):
            valid_mask = valid_mask & (data != src.nodata)

        # Also mask to watershed if available
        if self.watershed_shape and self.watershed_geojson:
            try:
                geom = [self.watershed_geojson["features"][0]["geometry"]]
                masked, _ = rio_mask(src, geom, crop=False, nodata=np.nan)
                basin_mask = ~np.isnan(masked[0])
                valid_mask = valid_mask & basin_mask
            except Exception:
                pass

        abs_data = np.abs(data)
        abs_data[~valid_mask] = 0

        # Find top N pixels by absolute value
        flat_indices = np.argsort(abs_data.ravel())[-top_n:][::-1]
        rows, cols = np.unravel_index(flat_indices, data.shape)

        hotspots = []
        for r, c in zip(rows, cols):
            val = float(data[r, c])
            if np.isnan(val) or val == 0:
                continue

            # Convert pixel to coordinates
            lon, lat = src.xy(int(r), int(c))
            change_type = "improvement" if val > 0 else "degradation"

            hotspots.append({
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "value": round(val, 4),
                "abs_value": round(abs(val), 4),
                "type": change_type,
                "layer": layer_key,
            })

        if self._hotspots_cache is None:
            self._hotspots_cache = {}
        self._hotspots_cache[cache_key] = hotspots
        return hotspots

    def get_watershed_info(self) -> dict:
        """Return watershed identity and metadata."""
        info = {
            "name": "Gundlakamma Watershed",
            "district": "Prakasam",
            "state": "Andhra Pradesh",
            "project": "WDC-PMKSY",
            "boundary_type": "Approximate prototype boundary",
            "data_sources": [
                {"name": "Sentinel-2 L2A", "provider": "Copernicus/ESA", "date": "July 2026", "resolution": "~111 m (resampled)"},
                {"name": "Sentinel-2 L2A", "provider": "Copernicus/ESA", "date": "2025", "resolution": "~111 m (resampled)"},
                {"name": "CartoDEM", "provider": "NRSC/ISRO", "date": "Current", "resolution": "~30 m"},
                {"name": "Bhuvan LULC WMS", "provider": "NRSC/ISRO", "date": "2015-16", "resolution": "1:50,000 (visual only)"},
            ],
            "disclaimers": [
                "AOI is an approximate prototype boundary, not an official SLNA micro-watershed.",
                "DRISHTI field records are simulated mock data for demonstration purposes.",
                "Bhuvan LULC is a visual WMS overlay; no computed LULC statistics are derived from it.",
                "Pixel resolution is ~111 m; point-level analysis has corresponding spatial uncertainty.",
                "Two-date comparison (2025 vs 2026) is shown; this is NOT a long-term trend.",
            ],
        }

        if self.watershed_shape:
            bounds = self.watershed_shape.bounds
            info["bounds"] = {
                "west": round(bounds[0], 4),
                "south": round(bounds[1], 4),
                "east": round(bounds[2], 4),
                "north": round(bounds[3], 4),
            }
            info["center"] = {
                "latitude": round(self.watershed_shape.centroid.y, 4),
                "longitude": round(self.watershed_shape.centroid.x, 4),
            }
            # Approximate area in sq km (rough at this latitude)
            area_deg2 = self.watershed_shape.area
            area_km2 = area_deg2 * (111 ** 2) * math.cos(math.radians(15.35))
            info["approx_area_km2"] = round(area_km2, 1)

        return info

    def get_layers_catalog(self) -> list:
        """Return metadata about available map layers."""
        layers = [
            {
                "id": "satellite",
                "name": "Satellite Imagery",
                "type": "basemap",
                "source": "Esri World Imagery",
                "description": "High-resolution satellite base map",
                "always_on": True,
            },
            {
                "id": "watershed_boundary",
                "name": "Watershed Boundary",
                "type": "vector",
                "source": "Derived from research data",
                "description": "Approximate Gundlakamma watershed boundary",
                "default_on": True,
            },
            {
                "id": "ndvi",
                "name": "NDVI (Current - 2026)",
                "type": "overlay",
                "source": "Sentinel-2 L2A, July 2026",
                "description": "Normalized Difference Vegetation Index. Green = high vegetation, Red = bare soil.",
                "colormap": "RdYlGn",
                "default_on": True,
            },
            {
                "id": "ndvi_change",
                "name": "NDVI Change (2025-2026)",
                "type": "overlay",
                "source": "Computed from Sentinel-2",
                "description": "Vegetation change between 2025 and 2026. Blue = improvement, Red = degradation.",
                "colormap": "seismic_r",
                "default_on": False,
            },
            {
                "id": "ndwi",
                "name": "NDWI (Current - 2026)",
                "type": "overlay",
                "source": "Sentinel-2 L2A, July 2026",
                "description": "Normalized Difference Water Index. Blue = water/moisture presence.",
                "colormap": "Blues",
                "default_on": False,
            },
            {
                "id": "water_mask",
                "name": "Surface Water (2026)",
                "type": "overlay",
                "source": "Derived from NDWI threshold",
                "description": "Binary water detection mask.",
                "default_on": False,
            },
            {
                "id": "water_change",
                "name": "Water Change (2025-2026)",
                "type": "overlay",
                "source": "Computed from water masks",
                "description": "Water body extent change. Blue = new water, Red = water loss.",
                "default_on": False,
            },
            {
                "id": "drainage",
                "name": "Drainage Network",
                "type": "vector",
                "source": "Derived from CartoDEM",
                "description": "Stream/drainage network derived from digital elevation model.",
                "default_on": True,
            },
            {
                "id": "slope",
                "name": "Terrain Slope",
                "type": "overlay",
                "source": "CartoDEM 30m",
                "description": "Slope in degrees. Higher values indicate steeper terrain.",
                "colormap": "plasma",
                "default_on": False,
            },
            {
                "id": "bhuvan_lulc",
                "name": "Bhuvan LULC (2015-16)",
                "type": "wms",
                "source": "NRSC Bhuvan WMS",
                "description": "Land Use / Land Cover from Bhuvan. Visual overlay only; no statistics computed.",
                "default_on": False,
            },
            {
                "id": "drishti_records",
                "name": "Field Observations (DRISHTI)",
                "type": "markers",
                "source": "Mock DRISHTI data",
                "description": "Simulated field observation points with geo-tagged photos.",
                "default_on": True,
            },
        ]
        return layers
