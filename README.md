# SIH 26015: Geospatial Techniques for Watershed Development

## Project Setup & Data Acquisition

This directory contains the data acquisition scripts, test results, spatial analysis, and the mock field-data ingestion backend for SIH 2026 Problem Statement 26015.

Our Area of Interest (AOI) is the **Gundlakamma River Basin in Prakasam District, Andhra Pradesh**.

### Key Findings: Bhuvan / SRISHTI Limitations
As documented in `feasibility_report.md` and `docs/DRISHTI_Integration_Strategy.md`:
1.  **Bhuvan Thematic APIs** are currently offline/returning 404.
2.  **SRISHTI / DRISHTI** is a closed government portal with no public API for retrieving field photos.

### The Solution Architecture
We bypass these roadblocks by building a custom geospatial assessment engine that demonstrates the *capabilities* required by the problem statement:
1.  **Satellite Pipeline:** Pulls Sentinel-2 L2A data from Copernicus (CDSE) and calculates NDVI/NDWI.
2.  **Field Pipeline:** Provides a mock API to ingest simulated DRISHTI field records (photos + GPS).
3.  **Assessment Engine:** Cross-references the field GPS coordinates with the satellite raster data to generate automated analytical insights.

---

### Directory Structure

*   **`feasibility_report.md`**: **CRITICAL READING.** This document details the reality of accessing NRSC data (Bhuvan, Bhoonidhi, DRISHTI) and outlines the necessary strategic pivot for the hackathon prototype.

### Execution

To re-run the geometry acquisition:
```bash
python scripts/get_watershed_geometry.py
```

To re-run the API tests (requires setting the token):
**PowerShell:**
```powershell
$env:BHUVAN_API_TOKEN="your_token_here"
$env:PYTHONIOENCODING="utf-8"
python scripts/test_bhuvan_api.py
```

### Key Findings & Next Steps

As detailed in the `feasibility_report.md`, relying on live connections to Bhuvan APIs or the internal DRISHTI system is not viable for this hackathon due to offline services and restricted access.

**The path forward involves:**
1.  Using **Sentinel-2 data from Copernicus** for current watershed conditions (analyzed using the logic in `process_satellite_imagery.py`).
2.  Using the geometric boundaries in `downloaded_data/bhuvan` to clip the satellite imagery to our AOI.
3.  Building a custom interface to ingest mock "DRISHTI-style" geo-tagged photos to demonstrate the required integration.
