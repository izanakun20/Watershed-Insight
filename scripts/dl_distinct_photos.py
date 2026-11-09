import urllib.request, urllib.parse, json, os, shutil, time

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

CATEGORIES = {
    'Check Dam': 'Check_dams_in_India',
    'Stop Dam': 'Check_dams_in_India',
    'Farm Pond': 'Village_ponds_in_India',
    'Terracing': 'Terrace_agriculture_in_India',
    'Contour Bunding': 'Contour_ploughing',
    'Gully Plugs': 'Gully_erosion',
    'Trenching': 'Trenches',
    'Afforestation': 'Tree_planting_in_India',
    'Pasture Development': 'Cattle_of_India',
    'Agro-forestry': 'Agroforestry',
    'Percolation Tank': 'Water_conservation_in_India'
}

type_urls = {} 

print("Finding multiple images per category...")
for itype, cat in CATEGORIES.items():
    urls = []
    url = f"https://commons.wikimedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:{cat}&cmtype=file&cmlimit=10&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            members = data.get('query', {}).get('categorymembers', [])
            for m in members:
                title = m['title']
                if not title.lower().endswith(('.jpg', '.jpeg')): continue
                iurl = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&format=json"
                ireq = urllib.request.Request(iurl, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(ireq, timeout=10) as ir:
                    idata = json.loads(ir.read())
                    pages = idata.get('query', {}).get('pages', {})
                    for pid, pdata in pages.items():
                        if 'imageinfo' in pdata:
                            urls.append(pdata["imageinfo"][0]["url"])
    except Exception as e:
        print(f"Error fetching {itype}: {e}")
    type_urls[itype] = urls
    print(f"{itype}: found {len(urls)} images")

def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)

type_counters = {k: 0 for k in type_urls.keys()}
for fn in os.listdir(RECORDS_DIR):
    if not fn.endswith('.json'): continue
    path = os.path.join(RECORDS_DIR, fn)
    with open(path, "r") as f:
        rec = json.load(f)
    
    itype = rec.get("intervention_type", "Check Dam")
    rid = rec.get("id") or rec.get("record_id") or fn.replace(".json", "")
    tgt = os.path.join(PHOTOS_DIR, rid + ".jpg")
    
    pool = type_urls.get(itype)
    if not pool:
        pool = type_urls.get('Check Dam')
    
    if pool and len(pool) > 0:
        url = pool[type_counters[itype] % len(pool)]
        type_counters[itype] += 1
        
        print(f"DL {itype} -> {rid}")
        try:
            download(url, tgt)
        except Exception as e:
            print(f"Failed to DL {url}: {e}")
            
    rec["photo_filename"] = rid + ".jpg"
    rec["photo_url"] = f"/api/drishti/photos/{rid}.jpg"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2)

print("Synching to v2...")
import subprocess
subprocess.run('powershell -Command "Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\photos\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\photos\\; Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\records\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\records\\"', shell=True)
print("Done.")
