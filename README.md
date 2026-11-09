<div align="center">

# 🛰️ Watershed Insight
### Geospatial Intelligence & Ground-Truth Verification Platform for Watershed Development

[![SIH 2026](https://img.shields.io/badge/SIH_2026-Problem_Statement_26015-blue?style=for-the-badge&logo=target)](https://sih.gov.in)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Sentinel-2](https://img.shields.io/badge/Copernicus-Sentinel--2_L2A-4B6F44?style=for-the-badge)](https://dataspace.copernicus.eu/)
[![OpenRouter AI](https://img.shields.io/badge/Vision_AI-GPT--4o--mini-purple?style=for-the-badge)](https://openrouter.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Bridging Orbital Remote Sensing and Smartphone Field Geotags to Validate Watershed Interventions.</b><br>
  Engineered for the <b>WDC-PMKSY</b> monitoring mandate under the <b>Ministry of Rural Development (DoLR)</b> & <b>ISRO/NRSC</b>.
</p>

[Explore Features](#-core-capabilities) • [Architecture](#-system-architecture) • [Cross-Check Logic](#-deterministic-cross-verification-engine) • [Quick Start](#-quick-start--installation) • [API Specs](#-rest-api-catalog)

</div>

---

## 🌍 The Problem & The Vision

Under India's **Watershed Development Component of Pradhan Mantri Krishi Sinchayee Yojana (WDC-PMKSY)**, hundreds of thousands of water-harvesting structures (check dams, farm ponds, percolation tanks) and soil-conservation treatments (contour trenching, afforestation) are executed each year. 

Field teams record progress via geo-tagged photos (**NRSC DRISHTI**). However, monitoring outcomes faces critical challenges:
* **The Ground-Space Disconnect:** Photos show local masonry, but can't verify whether moisture retention, biomass density, or impounded water actually responded as planned.
* **Closed Portals & Service Outages:** DRISHTI field-photo feeds are restricted to internal networks, and legacy Bhuvan thematic endpoints often experience downtime.
* **Audit Scalability:** Reviewing thousands of geotagged submissions manually is error-prone and labor-intensive.

**Watershed Insight** solves this by establishing a **closed-loop validation engine**: pairing high-resolution **Copernicus Sentinel-2 (10m)** satellite time-series imagery and **CartoDEM (30m)** hydrological models with on-the-ground geotagged mobile records.

```
       ORBITAL OBSERVATION (10m Sentinel-2)               FIELD EVIDENCE (DRISHTI Mobile)
       [NDVI • NDWI • Water Masks • Change]              [Geotagged Photo • GPS • Stage]
                         \                                      /
                          \                                    /
                           ▼                                  ▼
               ┌──────────────────────────────────────────────────┐
               │    WATERSHED INSIGHT CROSS-VERIFICATION CORE     │
               │   Deterministic GIS Spatial & Spectral Analysis  │
               └──────────────────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
   🎯 Verification Verdict                              🤖 Multimodal AI Advisory
  Consistent | Inconclusive | Field Audit                Intervention classification &
  with transparent spectral metrics                      contextual agronomic assessment
```

> **Target Area of Interest (AOI):**  
> **Gundlakamma River Basin**, Prakasam District, Andhra Pradesh, India (`79.65°E, 15.33°N`).

---

## 🚀 Core Capabilities

### 1. 🛰️ Multi-Temporal Satellite Raster Engine
* **Bespoke Spectral Pipeline:** Automatically ingests Sentinel-2 L2A bottom-of-atmosphere reflectance bands (B02 Blue, B03 Green, B04 Red, B08 NIR).
* **Biophysical Indices:** Calculates 10-meter Normalized Difference Vegetation Index (**NDVI**) and Normalized Difference Water Index (**NDWI**).
* **2025 → 2026 Change Detection:** Renders differential vegetation and water masks, exposing multi-hectare conservation gains and environmental stress hotspots.
* **Terrain & Hydrography:** Derives digital elevation models, slopes, and watershed flow-accumulation streams using **CartoDEM 30m** and **pysheds**.

### 2. 🔍 Deterministic Field ↔ Satellite Cross-Verification
* Samples multi-band rasters directly at field observation coordinates.
* Applies a **fully explainable, rule-based audit engine** (not a black-box model) to evaluate whether satellite reality supports the claimed field work.
* Categorizes submissions into 3 transparent outcomes:
  * 🟢 **Consistent:** Spectral data confirms expected physical changes (e.g., detected surface water / moisture spike at a newly completed check dam).
  * 🟡 **Inconclusive:** Plausible intervention where signature is sub-pixel (e.g., rock check dams smaller than 10m spatial resolution) or affected by seasonal latency.
  * 🔴 **Field Verification Recommended:** Discrepancy observed (e.g., mature afforestation claimed over barren, high-degradation terrain).

### 3. 🧠 Multimodal AI Vision & Advisory (GPT-4o-mini via OpenRouter)
* **Visual Audit:** Inspects uploaded DRISHTI field photos to independently classify the intervention (Check Dam, Farm Pond, Gully Plug, Bunding, Afforestation, etc.) with confidence scores.
* **Contextual Advisory Generator:** Synthesizes GIS spectral numbers, slope angles, and field reports into concise, objective 2-paragraph summaries designed for district watershed project officers.
* **Scientific Integrity:** Strictly prompts the AI to use cautious, evidence-based phrasing (*"evidence suggests"*, *"spectral indicators are consistent with"*) rather than false claims of proof.

### 4. 🗺️ Civic Cartography Command Center (Frontend SPA)
* **Single-Page Architecture:** Zero external framework overhead — lightning fast vanilla JavaScript and custom-styled modern CSS.
* **Interactive Map Viewer:** Multi-layer Leaflet canvas featuring Esri World Imagery, dynamic GeoTIFF transparent overlays, vector stream networks, and Bhuvan LULC 50K WMS layers.
* **Before / After Comparison Slider:** Interactive split-screen visualizer comparing pre-treatment vs. post-treatment satellite captures.
* **Automated Executive Reporting:** One-click dossier generation compiling watershed KPIs, category distributions, recent alerts, and audit trails.

---

## 📐 System Architecture

```mermaid
flowchart TD
    subgraph Data Sources
        S2["Sentinel-2 L2A (10m)<br/>Copernicus CDSE API"]
        CD["CartoDEM (30m)<br/>ISRO / NRSC"]
        FD["DRISHTI Geo-Records<br/>Photos + Coordinates"]
    end

    subgraph Data Preprocessing Pipeline
        P1["process_s2_10m.py<br/>Mosaicing & AOI Clip"]
        P2["derive_drainage_and_slope.py<br/>Pysheds Stream Extraction"]
        P3["generate_web_overlays.py<br/>Transparent GeoTIFF to Web PNG"]
    end

    subgraph Backend Core (FastAPI)
        RS["RasterService<br/>GeoTIFF I/O & Zonal Stats"]
        CS["CrossCheckService<br/>Deterministic Rules Engine"]
        AI["AIService<br/>GPT-4o-mini Vision & Advisory"]
        API["FastAPI Endpoints<br/>RESTful JSON API"]
    end

    subgraph Frontend Client (Civic Cartography SPA)
        DASH["Dashboard & KPI Cards"]
        MAP["Monitor (Leaflet Map)"]
        FIELD["Field Ingestion & Upload"]
        ANALYSIS["Before/After Split Slider"]
        REPORT["Executive PDF/Print Dossier"]
    end

    S2 --> P1
    CD --> P2
    P1 --> RS
    P2 --> RS
    RS --> CS
    FD --> API
    API --> AI
    API --> CS
    API --> RS
    CS --> API
    AI --> API
    API --> DASH
    API --> MAP
    API --> FIELD
    API --> ANALYSIS
    API --> REPORT
```

---

## 🔬 Deterministic Cross-Verification Engine

The cross-check engine eliminates guesswork by running rigorous spatial and spectral audits:

| Intervention Category | Primary Spectral Test | Spatial / Terrain Check | Result Criteria | Status Output |
|-----------------------|-----------------------|-------------------------|-----------------|---------------|
| **Water Harvesting**<br>*(Check Dam, Nala Bund, Pond)* | NDWI moisture index & Binary Water Mask | Intersection with drainage corridors & flow paths | Water detected or elevated post-monsoon moisture | 🟢 **Consistent** |
| **Water Harvesting**<br>*(Sub-pixel structures)* | Low water reflectance at point | Flow accumulation stream present | Signal within expected dry-season or sub-pixel limits | 🟡 **Inconclusive** |
| **Biomass & Forestry**<br>*(Afforestation, Horticulture)* | Mean NDVI & Delta NDVI (2025→2026) | Slope stability check | $\Delta\text{NDVI} > +0.08$ with healthy baseline | 🟢 **Consistent** |
| **Biomass & Forestry**<br>*(Claimed vegetation)* | Low NDVI ($< 0.18$) & negative change | Within watershed boundary | Vegetation degradation detected despite claimed plantation | 🔴 **Field Audit Recommended** |
| **Soil Conservation**<br>*(Trenching, Bunding)* | Indirect vegetative vigor | High slope ($> 15\%$) runoff zone | Physical structures naturally smaller than 10m raster resolution | 🟡 **Inconclusive** *(Appropriate)* |

---

## 🗂️ Repository Structure

```
Watershed-Insight/
├── backend/
│   ├── main.py                     # FastAPI application & route declarations
│   ├── .env.example                # Environment variables template
│   └── services/
│       ├── raster_service.py       # GeoTIFF loading, sampling, zonal stats
│       ├── crosscheck_service.py   # Ground-to-satellite rule verification
│       └── ai_service.py           # GPT-4o-mini vision classifier & advisor
│
├── frontend/
│   ├── index.html                  # Single Page Application container
│   ├── app.js                      # Core UI controller & Leaflet integrations
│   ├── style.css                   # "Civic Cartography" responsive theme
│   └── img/                        # Satellite comparison assets & basemaps
│
├── docs/
│   ├── data_schema.md              # Complete raster/vector data dictionary
│   └── drishti_mock_schema.json    # JSON Schema definition for field geotags
│
├── mock_drishti_data/
│   ├── photos/                     # Representative field photos
│   └── records/                    # Standardized geo-tagged JSON records
│
├── processed_data/
│   ├── cartodem_drainage.geojson   # Extracted stream network
│   ├── scene_metadata.json         # Timestamp & sensor provenance
│   └── web/                        # Web-optimized map overlay layers
│       ├── bounds.json             # Map coordinates & bounding boxes
│       ├── ndvi.png, ndvi_change.png, ndwi.png
│       └── water_mask.png, water_change.png, slope.png
│
├── scripts/
│   ├── process_s2_10m.py           # Copernicus CDSE Sentinel-2 download pipeline
│   ├── process_satellite_imagery.py# NDVI/NDWI computation routines
│   ├── derive_drainage_and_slope.py# DEM drainage network modeling
│   ├── generate_web_overlays.py    # GeoTIFF to transparent RGBA PNG converter
│   └── generate_mock_drishti.py    # Synthetic DRISHTI dataset generator
│
├── feasibility_report.md           # Field notes on Bhuvan & NRSC API access realities
├── data_inventory.csv              # Multi-source dataset catalogue
└── .gitignore                      # Configured to protect secrets and large rasters
```

---

## ⚡ Quick Start & Installation

### Prerequisites
* **Python 3.10+**
* Modern web browser (Chrome, Edge, Firefox, Safari)
* *(Optional)* [OpenRouter API Key](https://openrouter.ai/keys) for automated photo classification

### 1. Clone the Repository
```bash
git clone https://github.com/izanakun20/Watershed-Insight.git
cd Watershed-Insight
```

### 2. Set Up the Backend
```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn rasterio shapely geopandas requests pillow python-dotenv
```

### 3. Configure Environment Variables
Create a `.env` file in the `backend/` directory:
```bash
cp .env.example .env
```
Open `.env` and add your OpenRouter API key (optional, fallback rules work without it):
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 4. Launch the Platform
Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

Now open your browser and navigate to:
```
http://localhost:8000/
```
The FastAPI backend serves the frontend SPA directly alongside all analytical REST endpoints.

---

## 📡 REST API Catalog

The backend exposes clean, fully documented endpoints:

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/api/watershed/info` | `GET` | `JSON` | AOI bounds, centroid coordinates, and sensor provenance |
| `/api/watershed/stats` | `GET` | `JSON` | Zonal statistics (mean/median NDVI, water extent, improved %) |
| `/api/layers/catalog` | `GET` | `JSON` | Metadata catalogue for all 10 visual map overlays |
| `/api/change/summary` | `GET` | `JSON` | Aggregated 2025→2026 biomass and hydrologic change metrics |
| `/api/change/hotspots` | `GET` | `JSON` | Coordinates of greatest vegetation gains & environmental distress |
| `/api/drishti/records` | `GET` | `JSON` | List all geotagged field monitoring observations |
| `/api/drishti/records/{id}/crosscheck` | `GET` | `JSON` | Run the cross-verification audit on an existing record |
| `/api/drishti/upload` | `POST` | `JSON` | Upload field photo + GPS → AI classify → GIS cross-check |
| `/api/dashboard/summary` | `GET` | `JSON` | Complete bundle powering the dashboard KPIs and tables |

---

## 🛡️ Scientific Disclaimers & Integrity

In accordance with rigorous remote sensing standards:
1. **Resolution Constraints:** Sentinel-2 features a **10-meter ground sampling distance**. Single masonry structures smaller than $10\text{m}\times 10\text{m}$ (e.g., loose boulder check dams) are physically sub-pixel and produce indirect hydrologic indicators rather than discrete structural outlines.
2. **Two-Epoch Baseline:** Change layers compare specific cloud-free acquisitions between **2025 and 2026**. Long-term climatological trends require multi-year longitudinal observation.
3. **Auxiliary Context:** Optical remote sensing assesses surface conditions; subsurface soil moisture and aquifer recharge require ground piezometer validation.

---

## 👥 Acknowledgments & Hackathon Context

Developed as an innovative prototype for **Smart India Hackathon (SIH) 2026** tackling **Problem Statement 26015**.

* **Ministry:** Ministry of Rural Development (Department of Land Resources) & ISRO / NRSC
* **Satellite Data:** European Space Agency (ESA) Copernicus Sentinel-2 L2A via CDSE
* **Terrain Data:** ISRO / NRSC CartoDEM 30m
* **Basemaps:** Esri World Imagery & OpenStreetMap Contributors

---

<div align="center">
  <sub>Built with ❤️ for precision watershed conservation and digital governance.</sub>
</div>
