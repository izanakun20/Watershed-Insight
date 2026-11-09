"""
Bhuvan API Test Script — SIH 26015
Prakasam district / Gundlakamma watershed, Andhra Pradesh

Run:
    $env:BHUVAN_API_TOKEN="46d8b1523b36fcfdf679c2a2b089edd73017aedd"
    python scripts/test_bhuvan_api.py

Results are saved to: scripts/api_test_results.json
"""

import os
import re
import sys
import json
import time
import datetime
import requests

# ── Auth ────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("BHUVAN_API_TOKEN")
if not TOKEN:
    sys.exit(
        "[ERROR] BHUVAN_API_TOKEN not set.\n"
        "PowerShell: $env:BHUVAN_API_TOKEN='<your_token>'\n"
        "bash:       export BHUVAN_API_TOKEN='<your_token>'"
    )

BASE = "https://bhuvan-app1.nrsc.gov.in/api"
TIMEOUT = 45

SESSION = requests.Session()
SESSION.headers.update({
    "token": TOKEN,
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/html, */*",
    "User-Agent": "SIH26015-DataAcquisition/1.0",
})

# ── Prakasam AOI ─────────────────────────────────────────────────────────────
# Gundlakamma river basin, Prakasam district, AP
# WGS84 approximate bounding polygon
GUNDLAKAMMA_POLYGON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [79.0, 14.8],
            [80.2, 14.8],
            [80.2, 15.8],
            [79.0, 15.8],
            [79.0, 14.8],
        ]],
    },
    "properties": {"name": "Gundlakamma Basin Approx — Prakasam AP"},
}

# Prakasam district bounding box polygon (broader)
PRAKASAM_DISTRICT_POLYGON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [78.8, 14.5],
            [80.5, 14.5],
            [80.5, 16.0],
            [78.8, 16.0],
            [78.8, 14.5],
        ]],
    },
    "properties": {"name": "Prakasam District Approximate"},
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def _parse(resp: requests.Response):
    try:
        return {"status": "json", "data": resp.json()}
    except Exception:
        text = resp.text
        for pat in (r"(\[.*?\])", r"(\{.*?\})"):
            m = re.search(pat, text, re.DOTALL)
            if m:
                try:
                    return {"status": "json_from_html", "data": json.loads(m.group(1))}
                except Exception:
                    pass
        return {
            "status": "raw_html",
            "data": text[:2000],
            "length": len(text),
        }


def test_endpoint(name: str, method: str, url: str, **kwargs) -> dict:
    result = {
        "name": name,
        "url": url,
        "method": method,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    try:
        if method.upper() == "GET":
            resp = SESSION.get(url, timeout=TIMEOUT, **kwargs)
        else:
            resp = SESSION.post(url, timeout=TIMEOUT, **kwargs)

        result["http_status"] = resp.status_code
        result["content_type"] = resp.headers.get("Content-Type", "")
        result["response_size_bytes"] = len(resp.content)

        if resp.status_code == 200:
            result["success"] = True
            result["parsed"] = _parse(resp)
        else:
            result["success"] = False
            result["error"] = f"HTTP {resp.status_code}"
            result["response_preview"] = resp.text[:500]

    except requests.exceptions.Timeout:
        result["success"] = False
        result["error"] = "TIMEOUT"
    except requests.exceptions.ConnectionError as e:
        result["success"] = False
        result["error"] = f"CONNECTION_ERROR: {e}"
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


# ── Tests ────────────────────────────────────────────────────────────────────
results = []

print("=" * 64)
print("Bhuvan API Tests — Prakasam / Gundlakamma Watershed")
print("=" * 64)
print(f"Token (first 8 chars): {TOKEN[:8]}...")
print()

# 1. LULC 50K Statistics — Prakasam district, each year
for year_code, year_label in [("0506","2005-06"), ("1112","2011-12"), ("1516","2015-16")]:
    name = f"LULC 50K Stats — Prakasam ({year_label})"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "GET", f"{BASE}/lulcstat50k.php",
        params={
            "state":    "Andhra Pradesh",
            "district": "Prakasam",
            "year":     year_code,
            "token":    TOKEN,
        },
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    if r.get("success") and r.get("parsed", {}).get("data"):
        d = r["parsed"]["data"]
        if isinstance(d, list) and d:
            print(f"  → {len(d)} LULC classes returned")
            print(f"  → First row: {d[0]}")
    time.sleep(0.5)

print()

# 2. LULC 50K AOI Wise — Gundlakamma polygon
for year_code, year_label in [("0506","2005-06"), ("1112","2011-12"), ("1516","2015-16")]:
    name = f"LULC 50K AOI Wise — Gundlakamma ({year_label})"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "POST", f"{BASE}/lulcaoi50k.php",
        data={
            "aoi":   json.dumps(GUNDLAKAMMA_POLYGON),
            "year":  year_code,
            "token": TOKEN,
        },
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    if r.get("success") and r.get("parsed", {}).get("data"):
        d = r["parsed"]["data"]
        if isinstance(d, list) and d:
            print(f"  → {len(d)} classes in AOI")
            print(f"  → First row: {d[0]}")
    time.sleep(0.5)

print()

# 3. LULC 250K Statistics — Andhra Pradesh
for year in ["2005", "2011"]:
    name = f"LULC 250K Stats — Andhra Pradesh ({year})"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "GET", f"{BASE}/lulcstat250k.php",
        params={"state": "Andhra Pradesh", "year": year, "token": TOKEN},
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    time.sleep(0.5)

print()

# 4. LULC 250K AOI Wise
for year in ["2005", "2011"]:
    name = f"LULC 250K AOI Wise — Gundlakamma ({year})"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "POST", f"{BASE}/lulcaoi250k.php",
        data={
            "aoi":   json.dumps(GUNDLAKAMMA_POLYGON),
            "year":  year,
            "token": TOKEN,
        },
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    time.sleep(0.5)

print()

# 5. Village Geocoding — sample village in Prakasam
for village in ["Markapur", "Ongole", "Kandukur"]:
    name = f"Village Geocoding — {village}"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "GET", f"{BASE}/vg.php",
        params={
            "village":  village,
            "district": "Prakasam",
            "state":    "Andhra Pradesh",
            "token":    TOKEN,
        },
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    time.sleep(0.3)

print()

# 6. Try alternate endpoint names used by Bhuvan JS router
for ep_name, ep_path in [
    ("dist.php",  f"{BASE}/dist.php"),
    ("aoi.php",   f"{BASE}/aoi.php"),
    ("point.php", f"{BASE}/point.php"),
    ("laoi.php",  f"{BASE}/laoi.php"),
]:
    name = f"Alt endpoint: {ep_name}"
    print(f"[TEST] {name}")
    r = test_endpoint(
        name, "GET", ep_path,
        params={"token": TOKEN, "state": "Andhra Pradesh"},
    )
    results.append(r)
    status = "OK" if r["success"] else "FAIL"
    print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
    time.sleep(0.3)

print()

# 7. WMS GetCapabilities (no token needed)
print("[TEST] Bhuvan WMS GetCapabilities")
r = test_endpoint(
    "WMS GetCapabilities", "GET",
    "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
    params={"service": "WMS", "version": "1.1.1", "request": "GetCapabilities"},
)
r_wms = r
results.append(r)
status = "OK" if r["success"] else "FAIL"
print(f"  {status} HTTP {r.get('http_status','N/A')} — {r.get('error', 'OK')}")
if r.get("success"):
    text = r.get("parsed", {}).get("data", "")
    if isinstance(text, str):
        lulc_count = text.lower().count("lulc")
        print(f"  → Response length: {r.get('response_size_bytes',0)} bytes")
        print(f"  → LULC mentions: {lulc_count}")

print()

# 8. WMS GetMap test (small tile over Prakasam)
print("[TEST] Bhuvan WMS GetMap (LULC 50K 2011-12, small tile)")
r = test_endpoint(
    "WMS GetMap LULC 50K 1112", "GET",
    "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
    params={
        "service":     "WMS",
        "version":     "1.1.1",
        "request":     "GetMap",
        "layers":      "bhuvan:BR_LULC50K_1112",
        "bbox":        "79.0,14.8,80.2,15.8",
        "width":       "256",
        "height":      "256",
        "srs":         "EPSG:4326",
        "format":      "image/png",
        "transparent": "TRUE",
    },
)
results.append(r)
status = "OK" if r["success"] else "FAIL"
print(f"  {status} HTTP {r.get('http_status','N/A')} — "
      f"Content-Type: {r.get('content_type','')} — "
      f"Size: {r.get('response_size_bytes',0)} bytes")

print()
print("=" * 64)
print("Summary:")
passed = sum(1 for x in results if x.get("success"))
failed = len(results) - passed
print(f"  Passed: {passed} / {len(results)}")
print(f"  Failed: {failed} / {len(results)}")
print("=" * 64)

# ── Save results ──────────────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(__file__), "api_test_results.json")

# Scrub token from saved results before writing
results_clean = []
for r in results:
    r2 = json.loads(json.dumps(r).replace(TOKEN, "***TOKEN***"))
    results_clean.append(r2)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results_clean, f, indent=2, ensure_ascii=False)
print(f"\nResults saved to: {out_path}")
