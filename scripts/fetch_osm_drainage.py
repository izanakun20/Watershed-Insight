import requests
import json
import os

bbox = "14.90,78.95,15.75,80.35" # minlat, minlon, maxlat, maxlon for Overpass
overpass_url = "http://overpass-api.de/api/interpreter"

# We query for rivers and streams within the bounding box
query = f"""
[out:json][timeout:50];
(
  way["waterway"="river"]({bbox});
  way["waterway"="stream"]({bbox});
  way["waterway"="drain"]({bbox});
  way["waterway"="canal"]({bbox});
);
out body;
>;
out skel qt;
"""

print("Querying Overpass API for drainage networks...")
response = requests.post(overpass_url, data={'data': query}, headers={'User-Agent': 'SIH-26015-Agent'})

if response.status_code == 200:
    data = response.json()
    
    # Simple conversion to GeoJSON
    features = []
    nodes = {node['id']: (node['lon'], node['lat']) for node in data['elements'] if node['type'] == 'node'}
    
    for element in data['elements']:
        if element['type'] == 'way':
            coords = []
            for node_id in element['nodes']:
                if node_id in nodes:
                    coords.append(nodes[node_id])
            if coords:
                features.append({
                    "type": "Feature",
                    "properties": element.get("tags", {}),
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    }
                })
                
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    os.makedirs("processed_data", exist_ok=True)
    out_path = "processed_data/drainage_osm_fallback.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    print(f"Saved {len(features)} drainage features to {out_path}.")
else:
    print("Failed to fetch drainage:", response.status_code)
