import os
import json
import uuid
import random
import datetime
from shapely.geometry import shape, Point
from PIL import Image, ImageDraw

def generate_mock_data(num_records=15):
    # Setup directories
    data_dir = "mock_drishti_data"
    photos_dir = os.path.join(data_dir, "photos")
    records_dir = os.path.join(data_dir, "records")
    os.makedirs(photos_dir, exist_ok=True)
    os.makedirs(records_dir, exist_ok=True)

    # Load watershed boundary to ensure valid coordinates
    basin_path = "downloaded_data/bhuvan/gundlakamma_basin_approx.geojson"
    with open(basin_path, "r", encoding="utf-8") as f:
        basin_json = json.load(f)
    
    # We use the first feature's geometry as the boundary
    watershed_shape = shape(basin_json["features"][0]["geometry"])
    minx, miny, maxx, maxy = watershed_shape.bounds

    intervention_map = {
        "Water Harvesting": ["Check Dam", "Percolation Tank", "Farm Pond", "Stop Dam"],
        "Soil Conservation": ["Contour Bunding", "Trenching", "Gully Plugs", "Terracing"],
        "Vegetation/Biomass": ["Afforestation", "Pasture Development", "Agro-forestry"]
    }
    stages = ["Pre-treatment", "During Work", "Completed"]
    uploaders = ["Nodal_Officer_A", "Nodal_Officer_B", "PIA_Inspector_1"]

    def get_random_point_in_polygon():
        while True:
            p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
            if watershed_shape.contains(p):
                return p.y, p.x  # lat, lon

    def create_placeholder_image(filepath, text):
        img = Image.new('RGB', (400, 300), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 140), text, fill=(255, 255, 0))
        img.save(filepath)

    generated_records = []

    for i in range(num_records):
        lat, lon = get_random_point_in_polygon()
        record_id = str(uuid.uuid4())
        
        category = random.choice(list(intervention_map.keys()))
        intervention = random.choice(intervention_map[category])
        stage = random.choice(stages)
        
        # Generate timestamp in the last 30 days
        days_ago = random.randint(0, 30)
        ts = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
        
        photo_filename = f"{record_id}.jpg"
        photo_path = os.path.join(photos_dir, photo_filename)
        create_placeholder_image(photo_path, f"MOCK PHOTO\n{intervention}\n{stage}")

        record = {
            "record_id": record_id,
            "timestamp": ts.isoformat(),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "gps_accuracy_m": round(random.uniform(2.0, 10.0), 1),
            "bearing": random.randint(0, 359),
            "watershed_id": "83",
            "project_id": "WDC-PMKSY-PRAKASAM",
            "intervention_category": category,
            "intervention_type": intervention,
            "intervention_stage": stage,
            "description": f"MOCK DATA: Routine {stage.lower()} field verification for {intervention}.",
            "photo_filename": photo_path,
            "uploader": random.choice(uploaders)
        }

        # Save individual JSON
        with open(os.path.join(records_dir, f"{record_id}.json"), "w") as f:
            json.dump(record, f, indent=2)
            
        generated_records.append(record)
    
    print(f"Successfully generated {num_records} mock records inside Gundlakamma watershed.")

if __name__ == "__main__":
    generate_mock_data(15)
