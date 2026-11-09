import os
import requests

CLIENT_ID = os.getenv("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("COPERNICUS_CLIENT_SECRET")

print("Authenticating...")
resp = requests.post(
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
)
resp.raise_for_status()
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("Searching Catalog for July 2025...")
bbox = [78.95, 14.90, 80.35, 15.75]
search_payload = {
    "collections": ["sentinel-2-l2a"],
    "datetime": "2025-07-01T00:00:00Z/2025-07-31T23:59:59Z",
    "bbox": bbox,
    "limit": 100
}
cat_resp = requests.post(
    "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search",
    headers=headers,
    json=search_payload
)
cat_resp.raise_for_status()
items = cat_resp.json().get("features", [])

if not items:
    print("No scenes found.")
else:
    best_cc = min(item.get("properties", {}).get("eo:cloud_cover", 100) for item in items)
    print(f"Found {len(items)} scenes in July 2025. Best cloud cover: {best_cc}%")
