import os
import json
import uuid
import datetime
import shutil

class DrishtiSimulator:
    def __init__(self, storage_dir="mock_drishti_db"):
        """Initialize the simulated DRISHTI database."""
        self.storage_dir = storage_dir
        self.photos_dir = os.path.join(storage_dir, "photos")
        self.records_dir = os.path.join(storage_dir, "records")
        
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.records_dir, exist_ok=True)

    def ingest_field_record(self, photo_filepath, latitude, longitude, watershed_id, intervention_type, stage="Completed", description=""):
        """
        Simulates a field officer clicking 'Upload' in the DRISHTI app.
        Takes the raw inputs, generates metadata, and stores it in our mock backend.
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Store the photo
        filename = os.path.basename(photo_filepath)
        safe_filename = f"{record_id}_{filename}"
        dest_photo_path = os.path.join(self.photos_dir, safe_filename)
        
        # Simulate upload by copying the file
        try:
            shutil.copy2(photo_filepath, dest_photo_path)
        except FileNotFoundError:
            print(f"[Warning] Photo file {photo_filepath} not found. Mocking upload anyway.")
            dest_photo_path = f"mocked_path/{safe_filename}"

        # 2. Build the JSON Record (matching our schema)
        record = {
            "record_id": record_id,
            "timestamp": timestamp,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy_meters": 3.2,  # Simulated GPS accuracy
                "bearing_degrees": 145   # Simulated compass bearing
            },
            "project_context": {
                "watershed_id": watershed_id,
            },
            "intervention": {
                "type": intervention_type,
                "stage": stage,
                "description": description
            },
            "media": {
                "photo_filename": safe_filename,
                "photo_url": dest_photo_path
            },
            "uploader": "nodal_officer_01"
        }

        # 3. Save to database (JSON file in this simulator)
        record_path = os.path.join(self.records_dir, f"{record_id}.json")
        with open(record_path, "w") as f:
            json.dump(record, f, indent=2)

        print(f"Successfully ingested DRISHTI record: {record_id}")
        return record

# Example Usage
if __name__ == "__main__":
    simulator = DrishtiSimulator(storage_dir="../processed_data/mock_drishti_db")
    
    # Let's ingest a mock check dam in the Gundlakamma basin
    simulator.ingest_field_record(
        photo_filepath="dummy_checkdam.jpg",
        latitude=15.3521,
        longitude=79.6432,
        watershed_id="83", # Gundlakamma sub-basin code
        intervention_type="Check Dam",
        stage="Completed",
        description="Constructed across tertiary stream to slow runoff and improve groundwater recharge."
    )
