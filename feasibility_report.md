# SIH 26015: Geospatial Techniques for Watershed Development - Feasibility Report

## What data do we ACTUALLY have for building SIH 26015?

This investigation focused on acquiring and verifying data for the Gundlakamma watershed in Prakasam, Andhra Pradesh, specifically targeting the tools and datasets developed by NRSC (Bhuvan, Bhoonidhi, SRISHTI/DRISHTI). 

Here is the realistic assessment of what is actually available vs. what is restricted or unavailable:

### 1. Bhuvan Thematic APIs (LULC Statistics)
**Status: OFFLINE / UNAVAILABLE**
*   **Finding:** We tested the Bhuvan APIs (`lulcstat50k.php`, `lulcaoi50k.php`, etc.) using a valid access token. All endpoints returned **HTTP 404 (Not Found)**.
*   **Impact:** We cannot programmatically retrieve LULC statistics or AOI-clipped data via the REST API at this time. The service appears to have been removed or relocated without public documentation updates.

### 2. Bhuvan WMS (Map Layers)
**Status: PARTIALLY AVAILABLE / UNRELIABLE**
*   **Finding:** We successfully connected to the Bhuvan WMS (`https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms`) and retrieved the `GetCapabilities` document. However, subsequent `GetMap` requests for specific LULC layers (e.g., `bhuvan:BR_LULC50K_1112`) returned XML errors stating `LayerNotDefined`.
*   **Impact:** We cannot rely on Bhuvan WMS for the core LULC visualization in our application right now, as the specific thematic layers seem to be missing from the server.

### 3. Bhoonidhi (Current Satellite Imagery)
**Status: AVAILABLE (Requires Registration)**
*   **Finding:** Bhoonidhi is the official ISRO portal for downloading Sentinel and IRS data. It requires user registration and manual download via their "Browse & Order" web interface. There is no simple public API for automated downloads without authenticated sessions.
*   **Alternative/Solution:** **Copernicus Data Space Ecosystem (ESA)**. This is the primary, global source for Sentinel-2 data. It provides the exact same imagery (10m resolution, frequent revisit), offers robust APIs (OData), and is much easier to automate for current condition monitoring (NDVI, water extent).
*   **Impact:** We *can* acquire current, high-resolution imagery for Prakasam (Sentinel-2 tiles 44PNT, 44PMT), but we should use Copernicus APIs rather than trying to scrape Bhoonidhi.

### 4. SRISHTI / DRISHTI (Field Photos & Monitoring)
**Status: STRICTLY RESTRICTED / NO PUBLIC API**
*   **Finding:** DRISHTI is an internal tool for authorized government officials (SLNAs, PIAs) to upload geo-tagged photos for specific watershed projects (IWMP/WDC-PMKSY). There is **no public API** to access these photos, and they cannot be scraped.
*   **Impact for SIH:** We cannot build a live integration with the real DRISHTI database. 
*   **Solution:** We must build a *mock/simulator* for the field photo component of our solution. We can create an app/interface that allows users to upload geo-tagged photos, which our system then correlates with the satellite imagery, demonstrating *how* the integration would work if we had access to the DoLR systems.

### 5. Watershed Geometry (AOI Boundaries)
**Status: AVAILABLE (Via Third Parties)**
*   **Finding:** We successfully wrote a script that downloads the Prakasam district boundary from OpenStreetMap (Nominatim). We also generated an approximate bounding box for the Gundlakamma basin.
*   **Solution:** For the precise official watershed boundaries, we need to manually export the GeoJSON from the **India-WRIS WebGIS** (Watershed Atlas layer), or use the global **HydroSHEDS** dataset, clipped to our bounding box.

---

## Strategic Pivot for Prototype Development

Because the primary Bhuvan APIs are offline and SRISHTI/DRISHTI is a closed system, we cannot simply "plug in" to existing NRSC infrastructure. 

To win SIH 26015, we must build a **standalone analytical pipeline** that demonstrates the *capabilities* requested in the problem statement using open data.

**The Actionable Plan:**
1.  **Stop relying on Bhuvan APIs:** They are broken. We cannot fix them.
2.  **Use Copernicus Sentinel-2:** This will be our primary data source. We will write Python scripts to download current imagery for Prakasam and calculate NDVI (vegetation) and NDWI (water bodies).
3.  **Simulate DRISHTI:** We will build a feature that ingests user-provided geo-tagged photos and overlays them on our derived Sentinel-2 analysis maps.
4.  **Derive our own insights:** Instead of asking Bhuvan for statistics, we will calculate them ourselves from the Sentinel-2 data (e.g., "Vegetation increased by 15% in this micro-watershed between 2024 and 2025").

This approach fulfills the core requirement: *"Application of Geospatial Techniques for visualization and analysis to interpret Geo-Coded images to enhance watershed Development Outcomes."*
