# SIH 26015 — Data Schema Reference

## Raster Data (`processed_data/`)

| File | Description | Resolution | CRS | Bands | Value Range |
|---|---|---|---|---|---|
| `ndvi_clipped.tif` | NDVI 2026 (current) | ~111 m | EPSG:4326 | 1 | -1.0 to 1.0 |
| `ndvi_2025.tif` | NDVI 2025 | ~111 m | EPSG:4326 | 1 | -1.0 to 1.0 |
| `ndvi_change_2025_2026.tif` | NDVI difference (2026 − 2025) | ~111 m | EPSG:4326 | 1 | ~ -0.5 to 0.5 |
| `ndwi_clipped.tif` | NDWI 2026 (current) | ~111 m | EPSG:4326 | 1 | -1.0 to 1.0 |
| `ndwi_2025.tif` | NDWI 2025 | ~111 m | EPSG:4326 | 1 | -1.0 to 1.0 |
| `ndwi_change_2025_2026.tif` | NDWI difference (2026 − 2025) | ~111 m | EPSG:4326 | 1 | ~ -0.5 to 0.5 |
| `water_mask_clipped.tif` | Binary water mask 2026 | ~111 m | EPSG:4326 | 1 | 0 or 1 |
| `water_mask_2025.tif` | Binary water mask 2025 | ~111 m | EPSG:4326 | 1 | 0 or 1 |
| `water_change_2025_2026.tif` | Water change (binary diff) | ~111 m | EPSG:4326 | 1 | -1, 0, or 1 |
| `raw_bands.tif` | Sentinel-2 bands 2026 (B02/B03/B04/B08) | ~111 m | EPSG:4326 | 4 | 0–10000 |
| `raw_bands_2025.tif` | Sentinel-2 bands 2025 | ~111 m | EPSG:4326 | 4 | 0–10000 |
| `cartodem_clipped.tif` | CartoDEM elevation | ~30 m | EPSG:4326 | 1 | meters |
| `cartodem_slope.tif` | Slope from CartoDEM | ~30 m | EPSG:4326 | 1 | degrees |

## Vector Data

| File | Description | Format |
|---|---|---|
| `downloaded_data/bhuvan/gundlakamma_basin_approx.geojson` | Approximate watershed boundary | GeoJSON Polygon |
| `processed_data/cartodem_drainage.geojson` | Derived drainage network | GeoJSON LineString |
| `processed_data/drainage_osm_fallback.geojson` | OSM waterways fallback | GeoJSON |

## Web Overlays (`processed_data/web/`)

| File | Source Raster | Colormap |
|---|---|---|
| `ndvi.png` | `ndvi_clipped.tif` | RdYlGn, vmin=-0.2, vmax=0.8 |
| `ndvi_change.png` | `ndvi_change_2025_2026.tif` | seismic_r, vmin=-0.3, vmax=0.3 |
| `slope.png` | `cartodem_slope.tif` | plasma, vmin=0, vmax=20 |
| `bounds.json` | Leaflet bounds for all overlays | JSON |

## DRISHTI Mock Records (`mock_drishti_data/`)

### Record Schema
```json
{
  "record_id": "UUID string",
  "timestamp": "ISO 8601 datetime",
  "latitude": 15.xxx,
  "longitude": 79.xxx,
  "gps_accuracy_m": 2.1,
  "bearing": 146,
  "watershed_id": "83",
  "project_id": "WDC-PMKSY-PRAKASAM",
  "intervention_category": "Water Harvesting | Soil Conservation | Vegetation/Biomass",
  "intervention_type": "Check Dam | Percolation Tank | Farm Pond | ...",
  "intervention_stage": "Pre-treatment | During Work | Completed",
  "description": "text",
  "photo_filename": "mock_drishti_data/photos/{record_id}.jpg",
  "uploader": "PIA_Inspector_1"
}
```

### Intervention Categories & Types
- **Water Harvesting**: Check Dam, Percolation Tank, Farm Pond, Stop Dam
- **Soil Conservation**: Contour Bunding, Trenching, Gully Plugs, Terracing
- **Vegetation/Biomass**: Afforestation, Pasture Development, Agro-forestry

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/watershed/info` | Watershed identity and metadata |
| `GET` | `/api/watershed/stats` | Zonal statistics from rasters |
| `GET` | `/api/layers/catalog` | Available layer list |
| `GET` | `/api/change/summary` | Change detection summary |
| `GET` | `/api/change/hotspots` | Top change locations |
| `GET` | `/api/drishti/records` | All DRISHTI records |
| `GET` | `/api/drishti/records/{id}/crosscheck` | Field→satellite cross-check |
| `POST` | `/api/drishti/upload` | Upload new field record |
| `GET` | `/api/dashboard/summary` | Dashboard aggregate data |

## WMS Layers

| Service | Layer | Usage |
|---|---|---|
| `https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms` | `lulc:AP_LULC50K_1516` | Visual overlay only. No computed statistics. |

## Disclaimers (must appear in UI)
- AOI is an approximate prototype boundary, not an official SLNA micro-watershed
- DRISHTI records are simulated mock data for demonstration
- Bhuvan LULC is a visual WMS overlay; no computed LULC statistics
- Raster resolution is ~111 m; point-level analysis has corresponding uncertainty
- Two-date comparison (2025 vs 2026), not a long-term trend
