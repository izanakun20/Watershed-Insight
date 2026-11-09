import os
import json
import uuid
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import rasterio
from shapely.geometry import shape, Point

# ---------------------------------------------------------
# Pydantic Models for Schema Validation
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

class AssessmentResponse(BaseModel):
    record_id: str
    intervention: str
    location_valid: bool
    ndvi: Optional[float]
    ndwi: Optional[float]
    water_detected: bool
    assessment: str

# ---------------------------------------------------------
# Application State and Spatial Engine
# ---------------------------------------------------------
app = FastAPI(title="SIH 26015 - Mock DRISHTI Ingestion API")

# Global variables to hold spatial data references
watershed_shape = None
ndvi_src = None
ndwi_src = None
water_src = None

DATA_DIR = "mock_drishti_data/records"

@app.on_event("startup")
def load_spatial_data():
    global watershed_shape, ndvi_src, ndwi_src, water_src
    
    # Load watershed boundary
    basin_path = "downloaded_data/bhuvan/gundlakamma_basin_approx.geojson"
    if os.path.exists(basin_path):
        with open(basin_path, "r", encoding="utf-8") as f:
            basin_json = json.load(f)
            watershed_shape = shape(basin_json["features"][0]["geometry"])
    
    # Load TIFF files
    try:
        ndvi_src = rasterio.open("processed_data/ndvi_clipped.tif")
        ndwi_src = rasterio.open("processed_data/ndwi_clipped.tif")
        water_src = rasterio.open("processed_data/water_mask_clipped.tif")
    except Exception as e:
        print(f"Error loading TIFFs: {e}")

@app.on_event("shutdown")
def close_spatial_data():
    if ndvi_src: ndvi_src.close()
    if ndwi_src: ndwi_src.close()
    if water_src: water_src.close()

# ---------------------------------------------------------
# Spatial Assessment Logic
# ---------------------------------------------------------
def assess_location(lat: float, lon: float, intervention_type: str) -> dict:
    point = Point(lon, lat)
    
    # 1. Location Validation
    location_valid = False
    if watershed_shape and watershed_shape.contains(point):
        location_valid = True
        
    # 2. Extract Satellite Evidence
    ndvi_val = None
    ndwi_val = None
    water_detected = False
    
    if location_valid:
        # rasterio.sample expects a list of (x, y) tuples
        coords = [(lon, lat)]
        
        try:
            if ndvi_src:
                ndvi_gen = ndvi_src.sample(coords)
                ndvi_val = float(next(ndvi_gen)[0])
                
            if ndwi_src:
                ndwi_gen = ndwi_src.sample(coords)
                ndwi_val = float(next(ndwi_gen)[0])
                
            if water_src:
                water_gen = water_src.sample(coords)
                water_val = next(water_gen)[0]
                water_detected = bool(water_val == 1)
        except Exception as e:
            print(f"Error sampling rasters: {e}")
            
    import math
    if ndvi_val is not None and math.isnan(ndvi_val):
        ndvi_val = None
    if ndwi_val is not None and math.isnan(ndwi_val):
        ndwi_val = None

    # 3. Rule-Based Assessment Engine
    assessment_notes = []
    
    if not location_valid:
        assessment_notes.append("Location is OUTSIDE the Gundlakamma watershed boundary. Field verification required.")
    else:
        assessment_notes.append("Location is valid (inside watershed).")
        
        if ndvi_val is not None:
            if ndvi_val > 0.4:
                assessment_notes.append(f"High vegetation detected (NDVI: {ndvi_val:.2f}).")
            elif ndvi_val < 0.2:
                assessment_notes.append(f"Low vegetation/bare soil detected (NDVI: {ndvi_val:.2f}).")
        else:
            assessment_notes.append("NDVI data unavailable (possibly masked out/NODATA).")
                
        if water_detected:
            assessment_notes.append("Surface water detected at this location.")
        elif ndwi_val is not None and ndwi_val > 0:
            assessment_notes.append(f"Moisture/potential water presence nearby (NDWI: {ndwi_val:.2f}).")
            
        # Specific intervention rules
        if "Check Dam" in intervention_type or "Pond" in intervention_type:
            if water_detected or (ndwi_val and ndwi_val > 0):
                assessment_notes.append("Satellite confirms hydrological relevance for water harvesting structure.")
            else:
                assessment_notes.append("No standing water detected at this moment; structure may be dry.")
    
    return {
        "location_valid": location_valid,
        "ndvi": ndvi_val,
        "ndwi": ndwi_val,
        "water_detected": water_detected,
        "assessment": " ".join(assessment_notes)
    }

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.post("/api/drishti/records", response_model=AssessmentResponse)
def ingest_record(record: DrishtiRecord):
    """
    Ingest a new mock DRISHTI record, save it, and run spatial assessment.
    (AI Image Classification placeholder goes here in future pipeline)
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    record_path = os.path.join(DATA_DIR, f"{record.record_id}.json")
    
    # Save the record
    with open(record_path, "w") as f:
        f.write(record.model_dump_json(indent=2))
        
    # Run Assessment
    analysis = assess_location(record.latitude, record.longitude, record.intervention_type)
    
    return AssessmentResponse(
        record_id=record.record_id,
        intervention=record.intervention_type,
        location_valid=analysis["location_valid"],
        ndvi=analysis["ndvi"],
        ndwi=analysis["ndwi"],
        water_detected=analysis["water_detected"],
        assessment=analysis["assessment"]
    )

@app.get("/api/drishti/records/{record_id}", response_model=AssessmentResponse)
def get_record_assessment(record_id: str):
    """
    Retrieve an existing record and run its spatial assessment.
    """
    record_path = os.path.join(DATA_DIR, f"{record_id}.json")
    if not os.path.exists(record_path):
        raise HTTPException(status_code=404, detail="Record not found")
        
    with open(record_path, "r") as f:
        data = json.load(f)
        
    record = DrishtiRecord(**data)
    analysis = assess_location(record.latitude, record.longitude, record.intervention_type)
    
    return AssessmentResponse(
        record_id=record.record_id,
        intervention=record.intervention_type,
        location_valid=analysis["location_valid"],
        ndvi=analysis["ndvi"],
        ndwi=analysis["ndwi"],
        water_detected=analysis["water_detected"],
        assessment=analysis["assessment"]
    )

@app.get("/api/drishti/records")
def list_records():
    """List all ingested mock records."""
    if not os.path.exists(DATA_DIR):
        return {"records": []}
        
    files = [f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    return {"records": files}
