import urllib.request, urllib.parse, json, os, shutil, time

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Exact titles from Wikimedia Commons
TITLES = {
    'Check Dam': 'File:Cement check dam at Kokale.jpg',
    'Stop Dam': 'File:Dam at Jalpa de Canovas 2.jpg',
    'Farm Pond': 'File:Percolation tank Maharashtra.jpg',
    'Terracing': 'File:Rice terraces, Uttarakhand, India.jpg',
    'Contour Bunding': 'File:Contour bunding.jpg',
    'Gully Plugs': 'File:Nala Bunding in Barmer.jpg',
    'Trenching': 'File:Contour trench India.jpg',
    'Afforestation': 'File:Haritha Haram plantation Telangana.jpg',
    'Pasture Development': 'File:Cattle grazing in Deccan Plateau.jpg',
    'Agro-forestry': 'File:Agroforestry India.jpg',
    'Percolation Tank': 'File:Percolation tank Maharashtra.jpg'
}

def get_url(title):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            pages = data['query']['pages']
            for pid, pdata in pages.items():
                if 'imageinfo' in pdata:
                    return pdata["imageinfo"][0]["url"]
    except Exception as e:
        print(f"Error fetching {title}: {e}")
    return None

def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)

print("Fetching URLs...")
type_urls = {}
for k, title in TITLES.items():
    u = get_url(title)
    if u:
        type_urls[k] = u
        print(f"{k} -> {u}")
    else:
        print(f"{k} -> NOT FOUND")
    time.sleep(1)

# Fallback to check dam if missing
fallback_url = type_urls.get('Check Dam') or type_urls.get('Stop Dam')

type_cache = {}
for fn in os.listdir(RECORDS_DIR):
    if not fn.endswith('.json'): continue
    path = os.path.join(RECORDS_DIR, fn)
    with open(path, "r") as f:
        rec = json.load(f)
    
    itype = rec.get("intervention_type", "Check Dam")
    rid = rec.get("id") or rec.get("record_id") or fn.replace(".json", "")
    tgt = os.path.join(PHOTOS_DIR, rid + ".jpg")
    
    url = type_urls.get(itype, fallback_url)
    
    if itype in type_cache:
        shutil.copy2(type_cache[itype], tgt)
        print(f"COPY {itype} -> {rid}")
    else:
        if url:
            print(f"DL {itype} -> {rid} from {url}")
            try:
                download(url, tgt)
                type_cache[itype] = tgt
            except Exception as e:
                print(f"Failed to DL {url}: {e}")
                if fallback_url and url != fallback_url:
                    try:
                        download(fallback_url, tgt)
                        type_cache[itype] = tgt
                    except: pass
                
    rec["photo_filename"] = rid + ".jpg"
    rec["photo_url"] = f"/api/drishti/photos/{rid}.jpg"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2)

print("Synching to v2...")
import subprocess
subprocess.run('powershell -Command "Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\photos\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\photos\\; Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\records\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\records\\"', shell=True)
print("Done.")
