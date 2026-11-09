import os, json, urllib.request, time
import urllib.parse

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

SEARCH_TERMS = {
    "Check Dam": "check dam india",
    "Stop Dam": "stop dam",
    "Farm Pond": "farm pond",
    "Terracing": "terrace farming",
    "Contour Bunding": "contour bunding",
    "Gully Plugs": "gully plug",
    "Trenching": "trenching agriculture",
    "Afforestation": "afforestation",
    "Pasture Development": "pasture cattle",
    "Agro-forestry": "agroforestry",
    "Percolation Tank": "percolation tank",
}

def get_image_url(term):
    query = urllib.parse.quote(f"filetype:bitmap|{term}")
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={query}&gsrnamespace=6&gsrlimit=1&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            pages = data.get('query', {}).get('pages', {})
            for k, v in pages.items():
                if 'imageinfo' in v and len(v['imageinfo']) > 0:
                    img_url = v['imageinfo'][0]['url']
                    # Strip tracking query params
                    return img_url.split('?')[0]
    except Exception as e:
        print(f"Error fetching {term}: {e}")
    return None

def download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)

# Pre-fetch URLs
type_urls = {}
for itype, term in SEARCH_TERMS.items():
    print(f"Searching for {itype}...")
    url = get_image_url(term)
    if not url:
        # fallback to a generic dam if not found
        url = get_image_url("dam reservoir")
    type_urls[itype] = url
    print(f"  -> {url}")
    time.sleep(1)

# Now apply to records
type_cache = {}
for fn in os.listdir(RECORDS_DIR):
    if not fn.endswith(".json"): continue
    path = os.path.join(RECORDS_DIR, fn)
    with open(path, "r") as f:
        rec = json.load(f)
    
    itype = rec.get("intervention_type", "Check Dam")
    rid = rec.get("id") or rec.get("record_id") or fn.replace(".json", "")
    tgt = os.path.join(PHOTOS_DIR, rid + ".jpg")
    
    url = type_urls.get(itype) or type_urls["Check Dam"]
    
    if itype in type_cache:
        import shutil
        shutil.copy2(type_cache[itype], tgt)
        print(f"COPY {itype} -> {rid}")
    else:
        print(f"DL {itype} -> {rid} from {url}")
        try:
            download(url, tgt)
            type_cache[itype] = tgt
        except Exception as e:
            print(f"Failed to DL {url}: {e}")
            
    # update record
    rec["photo_filename"] = rid + ".jpg"
    rec["photo_url"] = f"/api/drishti/photos/{rid}.jpg"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2)

print("Done. Synching to v2...")
import subprocess
subprocess.run('powershell -Command "Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\photos\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\photos\\; Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\records\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\records\\"', shell=True)
print("Synched.")
