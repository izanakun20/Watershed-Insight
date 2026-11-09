import os
import requests
import json
import warnings
warnings.filterwarnings("ignore") # Ignore unverified HTTPS warnings

TOKEN = os.getenv("BHUVAN_API_TOKEN")
if not TOKEN:
    print("ERROR: BHUVAN_API_TOKEN environment variable not set.")
    exit(1)

BASE_URL = "https://bhuvan-app1.nrsc.gov.in/api/thematic"
WMS_URL = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"

# Gundlakamma approximate bounding box polygon
AOI_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [79.617174625574, 14.380370761459853],
        [80.16335648754163, 14.380370761459853],
        [80.16335648754163, 15.375544542241323],
        [79.617174625574, 15.375544542241323],
        [79.617174625574, 14.380370761459853]
    ]]
}

def analyze_failure(status_code, text):
    if status_code in [401, 403] or "invalid token" in text.lower() or "unauthorized" in text.lower():
        return "Authentication Failure (401/403 or Invalid Token)"
    elif status_code == 404:
        return "Endpoint Failure (404 Not Found - Script removed or renamed)"
    elif status_code >= 500:
        return f"Service Failure ({status_code} Internal Error)"
    elif status_code == 200 and not text.strip():
        return "Service Failure (200 OK but Blank Response)"
    elif status_code == 200 and "error" in text.lower():
        return "Service Failure (200 OK but Error inside Body)"
    else:
        return f"Other Failure (HTTP {status_code})"

def run_test(name, method, url, params=None, data=None):
    print(f"\n--- Testing: {name} ---")
    print(f"URL: {url}")
    try:
        if method == "GET":
            resp = requests.get(url, params=params, verify=False, timeout=15)
        else:
            resp = requests.post(url, data=data, verify=False, timeout=15)
            
        print(f"HTTP Status: {resp.status_code}")
        preview = resp.text[:500].strip()
        print(f"Response Body (preview): {preview if preview else '<BLANK>'}")
        
        if resp.status_code == 200 and preview and "error" not in preview.lower():
            print("Classification: SUCCESS")
        else:
            reason = analyze_failure(resp.status_code, resp.text)
            print(f"Classification: {reason}")
            
    except Exception as e:
        print(f"HTTP Status: N/A")
        print(f"Response Body: N/A")
        print(f"Classification: Request Exception ({str(e)})")


# 1. LULC 50K Statistics
run_test("1. LULC 50K Statistics (AP, 2015-16)", "GET", f"{BASE_URL}/lulcstat50k.php", params={
    "state": "Andhra Pradesh",
    "district": "Prakasam",
    "year": "1516",
    "token": TOKEN
})

# 2. LULC 50K AOI Wise
run_test("2. LULC 50K AOI Wise (2015-16)", "POST", f"{BASE_URL}/lulcaoi50k.php", data={
    "aoi": json.dumps(AOI_POLYGON),
    "year": "1516",
    "token": TOKEN
})

# 3. LULC 250K Statistics
run_test("3. LULC 250K Statistics (AP, 2011)", "GET", f"{BASE_URL}/lulcstat250k.php", params={
    "state": "Andhra Pradesh",
    "year": "2011",
    "token": TOKEN
})

# 4. LULC 250K AOI Wise
run_test("4. LULC 250K AOI Wise (2011)", "POST", f"{BASE_URL}/lulcaoi250k.php", data={
    "aoi": json.dumps(AOI_POLYGON),
    "year": "2011",
    "token": TOKEN
})

# 5. WMS GetCapabilities
print(f"\n--- Testing: 5. WMS GetCapabilities ---")
print(f"URL: {WMS_URL}")
try:
    resp = requests.get(WMS_URL, params={"service": "WMS", "version": "1.1.1", "request": "GetCapabilities"}, verify=False, timeout=15)
    print(f"HTTP Status: {resp.status_code}")
    
    if resp.status_code == 200:
        lulc_layers = [line.strip() for line in resp.text.split('\n') if 'lulc' in line.lower() and '<name>' in line.lower()]
        print(f"Response indicates LULC layers exist? {'YES' if lulc_layers else 'NO'}")
        if lulc_layers:
            print("Sample LULC layers found:")
            for l in list(set(lulc_layers))[:5]:
                print(f" - {l}")
        print("Classification: SUCCESS")
    else:
        print(f"Response Body (preview): {resp.text[:500]}")
        print(f"Classification: {analyze_failure(resp.status_code, resp.text)}")
except Exception as e:
    print(f"Classification: Request Exception ({str(e)})")

print("\nTests complete.")
