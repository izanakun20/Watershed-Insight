# SIH 26015 — FINAL ANTIGRAVITY BUILD PROMPT

## Context
PS 26015: Application of Geospatial Techniques for visualization and analysis to interpret Geo-Coded Images to enhance Watershed Development Outcomes.

Prototype: Gundlakamma / Prakasam, Andhra Pradesh.

We already have a working technical prototype:
- FastAPI backend
- Leaflet map
- Bhuvan LULC WMS
- Sentinel-2 2025/2026 data
- NDVI / NDWI / water-mask layers
- 2025→2026 change layers
- drainage GeoJSON
- mock DRISHTI records
- spatial assessment from actual raster values

The current UI is only a technical demo. REDESIGN the UI completely using the supplied Stitch designs as the visual reference.

## Verified data + limitations
Available:
- `gundlakamma_basin_approx.geojson`
- Sentinel-2 2025 and 2026
- NDVI / NDWI / water masks
- change layers
- drainage
- mock DRISHTI records
- Bhuvan LULC as visual WMS

Limitations:
- AOI is an approximate prototype boundary, NOT an official SLNA micro-watershed.
- Real DRISHTI API/photo repository is not publicly accessible; use mock DRISHTI data.
- Bhuvan LULC is visual/WMS only; do not invent computed LULC statistics.
- Do not invent data or analytical results.
- Do not call a two-date comparison a long-term trend.

## First technical check
VERIFY actual raster resolution before relying on point-level analysis.
If current Sentinel-2 outputs are ~100 m, reprocess at native practical resolution (10 m for B04/B08-based NDVI; appropriate resolution for chosen NDWI bands).
Do not assume documentation is correct.

## Product structure

### 1. MONITOR WATERSHED
- Overview
- Interactive map
- Layers: Satellite, LULC, NDVI, NDWI/Water, Drainage, Change
- 2025 vs 2026 comparison
- Flagged/high-change locations
- Field observations
- Evidence dashboard

### 2. FIELD / DRISHTI
- Upload field photo / create mock record
- Read/store photo, GPS, timestamp, intervention type, stage, description
- Validate point inside AOI
- Place record on map
- Run field↔satellite cross-check
- Show evidence and status:
  - Consistent
  - Inconclusive
  - Field verification recommended
- Saved records must appear in Monitor too

## HERO FEATURE
The core differentiator is:
DRISHTI field observation → GPS → satellite/GIS evidence → explainable cross-check → decision.

Use evidence language. Never say satellite data “proves” an intervention worked.
Not every intervention is satellite-visible.

## AI
Do NOT force AI into deterministic GIS work.

Use normal processing for:
- NDVI / NDWI
- water masks
- raster change
- spatial joins
- distance calculations
- zonal statistics
- transparent consistency rules

AI only for:
- optional field-photo classification/description
- final advisory report from structured computed evidence

Do NOT build impact-prediction ML without labelled ground truth.
Do NOT invent AI confidence scores.

## UI direction
Follow the supplied Stitch designs:
- modern Indian government/public-sector look
- clean, professional, trustworthy
- map-first but not cluttered
- strong overview cards
- readable charts
- restrained styling
- no unnecessary 3D/glassmorphism
- clear data provenance

Entry screen:
Do NOT require login for Round 1.
Show:
- Monitor Watershed
- Field / DRISHTI

Monitor:
- watershed identity
- key evidence cards
- clean map
- layers
- alerts/priority areas
- recent observations

Field:
- photo upload
- metadata
- photo preview
- intervention classification
- satellite evidence
- save

Analysis:
- before/after comparison
- vegetation change
- water change
- hotspots
- concise interpretation

Reports:
- evidence summary
- flagged locations
- advisory
- sources/disclaimers

## Architecture
Keep the existing core stack:
- React + Leaflet/React-Leaflet
- FastAPI
- rasterio / numpy / geopandas / shapely
- GeoTIFF + GeoJSON + SQLite/flat files

Suggested backend modules:
- watershed
- layers
- drishti
- analysis/change
- dashboard
- report
- raster service
- cross-check service
- optional classifier
- optional LLM

Do not add unnecessary services.

## Stitch / MCP
A Stitch API key/MCP connection is already configured in Antigravity.
Use Stitch only as design/reference support.
Do NOT add MCP to the shipped application unless a concrete requirement appears.

## Build order
1. Verify raster resolution.
2. Freeze data paths/schemas.
3. Stabilize backend APIs.
4. Implement Monitor UI from Stitch.
5. Implement Field/DRISHTI UI.
6. Implement field↔satellite cross-check carefully.
7. Implement Analysis/change screen.
8. Implement dashboard.
9. Add AI advisory last.
10. Run complete end-to-end demo.

## Demo story
Monitor → see watershed condition → inspect change → open flagged location → open DRISHTI record → cross-check satellite evidence → show status → generate advisory.

## Anti-hallucination rules
Before changing anything:
1. Inspect the existing files/data.
2. Reuse working components.
3. Make the smallest necessary change.
4. Test it.
5. Report exactly what changed.

Never claim something is implemented unless it was tested.
Never invent data, endpoints, values, datasets, or capabilities.
