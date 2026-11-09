import urllib.request, urllib.parse, json, os, shutil

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"

# Pages mapped to interventions
pages = {
    'Check Dam': 'Check_dam',
    'Stop Dam': 'Check_dam',
    'Terracing': 'Terrace_(agriculture)',
    'Contour Bunding': 'Contour_plowing',
    'Agro-forestry': 'Agroforestry',
    'Farm Pond': 'Retention_basin',
    'Percolation Tank': 'Retention_basin',
    'Afforestation': 'Afforestation',
    'Trenching': 'Trench',
    'Pasture Development': 'Pasture',
    'Gully Plugs': 'Gully'
}

type_urls = {}

def get_image_from_page(page_title):
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=images&titles={page_title}&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            pages_data = data['query']['pages']
            for pid, pdata in pages_data.items():
                if 'images' in pdata:
                    for img in pdata['images']:
                        title = img['title']
                        if title.lower().endswith(('.jpg', '.jpeg')):
                            return title
    except:
        pass
    return None

def get_image_url_from_commons(file_title):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(file_title)}&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            pages_data = data['query']['pages']
            for pid, pdata in pages_data.items():
                if 'imageinfo' in pdata:
                    return pdata["imageinfo"][0]["url"]
    except:
        pass
    return None

print("Finding images...")
for itype, page in pages.items():
    file_title = get_image_from_page(page)
    if file_title:
        img_url = get_image_url_from_commons(file_title)
        if img_url:
            type_urls[itype] = img_url
            print(f"{itype} -> {img_url}")
        else:
            print(f"{itype} -> NO URL FOUND")
    else:
        print(f"{itype} -> NO IMAGE ON PAGE")

def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)

type_cache = {}
for fn in os.listdir(RECORDS_DIR):
    if not fn.endswith('.json'): continue
    path = os.path.join(RECORDS_DIR, fn)
    with open(path, "r") as f:
        rec = json.load(f)
    
    itype = rec.get("intervention_type", "Check Dam")
    rid = rec.get("id") or rec.get("record_id") or fn.replace(".json", "")
    tgt = os.path.join(PHOTOS_DIR, rid + ".jpg")
    
    url = type_urls.get(itype) or type_urls.get('Check Dam')
    
    if itype in type_cache:
        shutil.copy2(type_cache[itype], tgt)
    else:
        if url:
            try:
                download(url, tgt)
                type_cache[itype] = tgt
                print(f"Downloaded for {itype}")
            except:
                print(f"Failed to DL {url}")
                
    rec["photo_filename"] = rid + ".jpg"
    rec["photo_url"] = f"/api/drishti/photos/{rid}.jpg"
    with open(path, "w") as f:
        json.dump(rec, f, indent=2)

print("Synching to v2...")
import subprocess
subprocess.run('powershell -Command "Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\photos\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\photos\\; Copy-Item -Recurse -Force c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015\\mock_drishti_data\\records\\* c:\\Users\\siddh\\.gemini\\antigravity\\scratch\\sih26015-v2\\mock_drishti_data\\records\\"', shell=True)
print("Done.")
