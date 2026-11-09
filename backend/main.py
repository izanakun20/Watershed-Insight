"""
SIH 26015 - Watershed Command Centre Platform API
FastAPI backend with full endpoint surface for watershed monitoring,
field observation management, and field-satellite cross-checks.
"""
import os
import json
import uuid
import shutil
import math
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.raster_service import RasterService
from services.crosscheck_service import CrossCheckService
from services.ai_service import ai_service

# ---------------------------------------------------------
# Base Paths
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS_DIR = os.path.join(BASE_DIR, "mock_drishti_data", "records")
PHOTOS_DIR = os.path.join(BASE_DIR, "mock_drishti_data", "photos")

os.makedirs(RECORDS_DIR, exist_ok=True)
os.makedirs(PHOTOS_DIR, exist_ok=True)

# ---------------------------------------------------------
# Services
# ---------------------------------------------------------
raster_svc = RasterService()
crosscheck_svc = CrossCheckService()

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class DrishtiRecord(BaseModel):
    record_id: str
    timestamp: str
    latitude: float
    longitude: float
    gps_accuracy_m: Optional[float] = None
    bearing: Optional[float] = None
    watershed_id: str
    project_id: Optional[str] = None
    intervention_category: str
    intervention_type: str
    intervention_stage: str
    description: Optional[str] = None
    photo_filename: str
    uploader: Optional[str] = None

class CrossCheckResponse(BaseModel):
    record_id: str
    reported_intervention: str
    ai_predicted_intervention: str
    ai_confidence: str
    intervention_category: str
    status: str
    evidence: list
    summary: str
    satellite_values: dict
    location_valid: bool
    data_provenance: str
    ai_advisory: str

# ---------------------------------------------------------
# Application Lifecycle
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Loading spatial data...")
    raster_svc.load()
    print("Spatial data loaded.")
    yield
    # Shutdown
    raster_svc.close()
    print("Spatial data closed.")

app = FastAPI(
    title="SIH 26015 - Watershed Command Centre Platform",
    description="Geospatial analysis API for watershed development monitoring",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Helper: Load all DRISHTI records
# ---------------------------------------------------------
def load_all_records() -> list:
    """Load all DRISHTI records from disk."""
    records = []
    if not os.path.exists(RECORDS_DIR):
        return records
    for fname in sorted(os.listdir(RECORDS_DIR)):
        if fname.endswith(".json"):
            with open(os.path.join(RECORDS_DIR, fname), "r", encoding="utf-8") as f:
                try:
                    records.append(json.load(f))
                except json.JSONDecodeError:
                    continue
    return records

# ---------------------------------------------------------
# API: Watershed Info
# ---------------------------------------------------------
@app.get("/api/watershed/info")
def get_watershed_info():
    """Return watershed identity, boundary, and provenance metadata."""
    return raster_svc.get_watershed_info()

@app.get("/api/watershed/stats")
def get_watershed_stats():
    """Return zonal statistics computed from rasters within the watershed."""
    stats = raster_svc.compute_zonal_stats()
    if not stats:
        raise HTTPException(status_code=503, detail="Zonal statistics not available. Rasters may not be loaded.")
    return {"stats": stats, "note": "Statistics computed from actual raster values within the approximate watershed boundary."}

# ---------------------------------------------------------
# API: Layers
# ---------------------------------------------------------
@app.get("/api/layers/catalog")
def get_layers_catalog():
    """Return metadata for all available map layers."""
    return {"layers": raster_svc.get_layers_catalog()}

# ---------------------------------------------------------
# API: Change Detection
# ---------------------------------------------------------
@app.get("/api/change/summary")
def get_change_summary():
    """Return summary of NDVI, NDWI, and water changes between 2025 and 2026."""
    stats = raster_svc.compute_zonal_stats()
    result = {}
    for key in ["ndvi_change", "ndwi_change", "water_change"]:
        if key in stats:
            result[key] = stats[key]
    return {
        "summary": result,
        "period": "2025 to 2026 (two-date comparison, NOT a long-term trend)",
        "note": "Changes computed from Sentinel-2 derived indices within the watershed boundary.",
    }

@app.get("/api/change/hotspots")
def get_change_hotspots(layer: str = "ndvi_change", top_n: int = 10):
    """Return top N locations with the largest changes."""
    if layer not in ["ndvi_change", "ndwi_change", "water_change"]:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {layer}. Use ndvi_change, ndwi_change, or water_change.")
    hotspots = raster_svc.get_hotspots(layer, top_n)
    return {
        "hotspots": hotspots,
        "layer": layer,
        "note": "Hotspots are pixels with the largest absolute change values within the watershed.",
    }

# ---------------------------------------------------------
# API: DRISHTI / Field Records
# ---------------------------------------------------------
@app.get("/api/drishti/records")
def list_drishti_records():
    """List all DRISHTI field records."""
    records = load_all_records()
    return {"records": records, "count": len(records)}

# Keep old endpoint for backward compatibility
@app.get("/api/drishti/records_full")
def list_drishti_records_compat():
    """Backward-compatible alias for /api/drishti/records."""
    return list_drishti_records()

@app.get("/api/drishti/records/{record_id}")
def get_drishti_record(record_id: str):
    """Get a single DRISHTI record by ID."""
    record_path = os.path.join(RECORDS_DIR, f"{record_id}.json")
    if not os.path.exists(record_path):
        raise HTTPException(status_code=404, detail="Record not found")
    with open(record_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/drishti/photos/{filename}")
def serve_photo(filename: str):
    """Serve a DRISHTI field photo by filename."""
    photo_path = os.path.join(PHOTOS_DIR, filename)
    if not os.path.exists(photo_path):
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(photo_path)

@app.get("/api/drishti/records/{record_id}/crosscheck")
def crosscheck_record(record_id: str):
    """Perform field-to-satellite cross-check for a DRISHTI record."""
    record_path = os.path.join(RECORDS_DIR, f"{record_id}.json")
    if not os.path.exists(record_path):
        raise HTTPException(status_code=404, detail="Record not found")

    with open(record_path, "r", encoding="utf-8") as f:
        record = json.load(f)

    lat = record["latitude"]
    lon = record["longitude"]

    location_valid = raster_svc.is_inside_watershed(lat, lon)
    raster_values = raster_svc.sample_point(lat, lon)

    result = crosscheck_svc.crosscheck(record, raster_values, location_valid)
    
    # Generate AI Advisory
    evidence_payload = {
        "reported_intervention": record.get("reported_intervention", record.get("intervention_type", "")),
        "ai_predicted_intervention": record.get("ai_predicted_intervention", "Unknown"),
        "ai_confidence": record.get("ai_confidence", "0.0"),
        "crosscheck_status": result["status"],
        "satellite_evidence": result["evidence"]
    }
    advisory_report = ai_service.generate_advisory(evidence_payload)

    return CrossCheckResponse(
        record_id=record_id,
        reported_intervention=record.get("reported_intervention", record.get("intervention_type", "")),
        ai_predicted_intervention=record.get("ai_predicted_intervention", "Unknown"),
        ai_confidence=str(record.get("ai_confidence", "0.0")),
        intervention_category=record.get("intervention_category", ""),
        status=result["status"],
        evidence=result["evidence"],
        summary=result["summary"],
        satellite_values={
            "ndvi": raster_values.get("ndvi_current"),
            "ndwi": raster_values.get("ndwi_current"),
            "water_detected": raster_values.get("water_current") == 1 if raster_values.get("water_current") is not None else False,
            "ndvi_change": raster_values.get("ndvi_change"),
        },
        location_valid=location_valid,
        data_provenance=result["data_provenance"],
        ai_advisory=advisory_report
    )

@app.post("/api/drishti/upload")
async def upload_drishti_record(
    photo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    intervention_category: str = Form(...),
    intervention_type: str = Form(...),
    intervention_stage: str = Form(...),
    description: str = Form(""),
    gps_accuracy_m: float = Form(None),
    uploader: str = Form("Web Upload"),
):
    """Upload a new DRISHTI field record with photo."""
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Validate location
    location_valid = raster_svc.is_inside_watershed(latitude, longitude)

    # Save photo
    photo_ext = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
    photo_filename = f"{record_id}{photo_ext}"
    photo_path = os.path.join(PHOTOS_DIR, photo_filename)

    with open(photo_path, "wb") as f:
        content = await photo.read()
        f.write(content)

    # Classify image using AI
    ai_type, ai_conf, ai_desc = ai_service.classify_image(content, photo.content_type or "image/jpeg")
    
    # Create record
    record = {
        "id": record_id,
        "timestamp": timestamp,
        "latitude": latitude,
        "longitude": longitude,
        "intervention_category": intervention_category,
        "intervention_type": intervention_type, # Frontend primary display (reported)
        "reported_intervention": intervention_type,
        "ai_predicted_intervention": ai_type,
        "ai_confidence": ai_conf,
        "ai_short_description": ai_desc,
        "intervention_stage": intervention_stage,
        "description": description,
        "gps_accuracy_m": gps_accuracy_m,
        "is_mock": False,
        "location_valid": location_valid,
        "uploader": uploader,
        "photo_filename": photo_filename,
        "photo_url": f"/api/drishti/photos/{photo_filename}",
    }

    record_path = os.path.join(RECORDS_DIR, f"{record_id}.json")
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    # ---------------------------------------------------------
    # Run immediate cross-check
    # ---------------------------------------------------------
    raster_values = raster_svc.sample_point(latitude, longitude)
    crosscheck_result = crosscheck_svc.crosscheck(record, raster_values, location_valid)

    # Determine if AI classification was successful
    AI_FAILURE_LABELS = {"Unknown", "Unknown (AI Disabled)", "Classification Failed"}
    ai_classification_failed = ai_type in AI_FAILURE_LABELS

    # Generate AI Advisory only when classification succeeded
    advisory_report = None
    if not ai_classification_failed:
        evidence_payload = {
            "reported_intervention": intervention_type,
            "ai_predicted_intervention": ai_type,
            "ai_confidence": ai_conf,
            "crosscheck_status": crosscheck_result["status"],
            "satellite_evidence": crosscheck_result["evidence"]
        }
        advisory_report = ai_service.generate_advisory(evidence_payload)

    # Combine results
    crosscheck_data = {
        "status": crosscheck_result["status"],
        "evidence": crosscheck_result["evidence"],
        "summary": crosscheck_result["summary"],
        "data_provenance": crosscheck_result["data_provenance"],
        "ai_advisory": advisory_report
    }

    return {
        "message": "Record uploaded and analyzed successfully",
        "record_id": record_id,
        "ai_classification": ai_type,
        "ai_confidence": ai_conf,
        "ai_short_description": ai_desc,
        "ai_classification_failed": ai_classification_failed,
        "location_valid": location_valid,
        "crosscheck": crosscheck_data
    }

@app.get("/api/advisory/{record_id}")
def get_advisory(record_id: str):
    """Generate an AI advisory report from computed evidence."""
    try:
        crosscheck = crosscheck_record(record_id)
    except HTTPException as e:
        raise e
        
    evidence_data = {
        "record_id": crosscheck.record_id,
        "intervention": crosscheck.intervention_type,
        "status": crosscheck.status,
        "evidence": crosscheck.evidence,
        "summary": crosscheck.summary,
        "data_provenance": crosscheck.data_provenance
    }
    
    advisory = ai_service.generate_advisory(evidence_data)
    
    return {
        "advisory": advisory,
        "record_id": record_id
    }

# ---------------------------------------------------------
# API: Dashboard Summary
# ---------------------------------------------------------
@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    """Aggregated data for the dashboard view."""
    records = load_all_records()
    stats = raster_svc.compute_zonal_stats()
    info = raster_svc.get_watershed_info()
    hotspots = raster_svc.get_hotspots("ndvi_change", 5)

    # Count records by category
    category_counts = {}
    stage_counts = {}
    for r in records:
        cat = r.get("intervention_category", "Unknown")
        stage = r.get("intervention_stage", "Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # KPI cards
    ndvi_stats = stats.get("ndvi_current", {})
    water_stats = stats.get("water_current", {})
    change_stats = stats.get("ndvi_change", {})

    kpis = {
        "mean_ndvi": ndvi_stats.get("mean"),
        "mean_ndvi_label": "Mean NDVI (2026)",
        "water_coverage_pct": water_stats.get("water_area_pct"),
        "water_coverage_label": "Water Coverage",
        "water_area_ha": water_stats.get("water_area_ha"),
        "vegetation_improved_pct": change_stats.get("improved_pct"),
        "vegetation_degraded_pct": change_stats.get("degraded_pct"),
        "total_field_records": len(records),
        "flagged_locations": len(hotspots),
    }

    # Recent records (latest 5)
    recent = sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)[:5]

    return {
        "watershed": {
            "name": info.get("name"),
            "district": info.get("district"),
            "state": info.get("state"),
            "approx_area_km2": info.get("approx_area_km2"),
        },
        "kpis": kpis,
        "category_counts": category_counts,
        "stage_counts": stage_counts,
        "recent_records": recent,
        "hotspots": hotspots,
    }

# ---------------------------------------------------------
# Static File Serving
# ---------------------------------------------------------
# Serve data files (rasters, geojsons, photos)
app.mount("/data", StaticFiles(directory=BASE_DIR), name="data")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))
