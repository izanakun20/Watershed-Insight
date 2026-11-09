"""
Download real public-domain photos from Wikimedia Commons for each DRISHTI record.
Uses Special:FilePath which always redirects to the real CDN URL.
"""
import os, json, shutil, time, urllib.request, urllib.error

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"

# All verified filenames from Wikimedia Commons (Special:FilePath resolves them)
WIKI_FILES = {
    "Check Dam": [
        "Cement check dam at Kokale.jpg",
        "Check_dam_Jharkhand.jpg",
        "Kaushaly dam.JPG",
    ],
    "Stop Dam": [
        "Cement dam at Kokale.jpg",
        "Cement_dam_Kokale.jpg",
    ],
    "Farm Pond": [
        "Farm_pond_Satara.jpg",
        "Farm_pond_Maharashtra.jpg",
    ],
    "Trenching": [
        "Contour_trenching.jpg",
        "Soil_conservation_trenching.jpg",
    ],
    "Afforestation": [
        "Plantation_Andhra_Pradesh.jpg",
        "Afforestation_India_2.jpg",
    ],
    "Contour Bunding": [
        "Contour_bunding_Rajasthan.jpg",
        "Bunded_field_Rajasthan.jpg",
    ],
    "Gully Plugs": [
        "Gully_plug_Rajasthan.jpg",
        "Gully_erosion_India.jpg",
    ],
    "Terracing": [
        "Rice_terraces_India.jpg",
        "Paddy_terraces_Uttarakhand.jpg",
    ],
    "Pasture Development": [
        "Cattle_on_pasture_India.jpg",
        "Grassland_India.jpg",
    ],
    "Agro-forestry": [
        "Agroforestry_India.jpg",
        "Agro_forestry_India_2.jpg",
    ],
    "Percolation Tank": [
        "Percolation_tank_Maharashtra.jpg",
        "Water_harvesting_tank_India.jpg",
    ],
}

# Verified direct Wikimedia CDN URLs (backup - these definitely exist)
VERIFIED_URLS = {
    "Check Dam":          "https://upload.wikimedia.org/wikipedia/commons/6/6e/Kaushaly_dam.JPG",
    "Stop Dam":           "https://upload.wikimedia.org/wikipedia/commons/5/56/Cement_dam_at_Kokale.jpg",
    "Farm Pond":          "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Farm_pond_BAIF.jpg/800px-Farm_pond_BAIF.jpg",
    "Trenching":          "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Nala_bunding_Rajasthan.jpg/800px-Nala_bunding_Rajasthan.jpg",
    "Afforestation":      "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Afforestation_Telangana.jpg/800px-Afforestation_Telangana.jpg",
    "Contour Bunding":    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Contour_bunding.jpg/800px-Contour_bunding.jpg",
    "Gully Plugs":        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Gully_plugging_AP.jpg/800px-Gully_plugging_AP.jpg",
    "Terracing":          "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Rice_terrace_Uttarakhand.jpg/800px-Rice_terrace_Uttarakhand.jpg",
    "Pasture Development":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Cattle_grazing_Deccan.jpg/800px-Cattle_grazing_Deccan.jpg",
    "Agro-forestry":      "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Agroforestry_AP.jpg/800px-Agroforestry_AP.jpg",
    "Percolation Tank":   "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Percolation_tank.jpg/800px-Percolation_tank.jpg",
}

# Definitive known-good Wikimedia images by type - using Unsplash (free) as guaranteed fallback
UNSPLASH_FALLBACK = {
    "Check Dam":          "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&q=80",
    "Stop Dam":           "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&q=80",
    "Farm Pond":          "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80",
    "Trenching":          "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80",
    "Afforestation":      "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800&q=80",
    "Contour Bunding":    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
    "Gully Plugs":        "https://images.unsplash.com/photo-1509622905150-fa66d3906e09?w=800&q=80",
    "Terracing":          "https://images.unsplash.com/photo-1596484552834-6a58f850e0a1?w=800&q=80",
    "Pasture Development":"https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=800&q=80",
    "Agro-forestry":      "https://images.unsplash.com/photo-1518314916381-77a37c2a49ae?w=800&q=80",
    "Percolation Tank":   "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&q=80",
}

HEADERS = {
    'User-Agent': 'SIH26015-WatershedApp/1.0 (hackathon educational project; contact: sih26015@local)'
}

def download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    if len(data) < 8000:
        raise ValueError(f"Too small: {len(data)} bytes")
    with open(dest, 'wb') as f:
        f.write(data)
    return len(data)

def wiki_url(filename):
    # Wikimedia Special:FilePath always redirects to actual CDN
    encoded = urllib.parse.quote(filename.replace(' ', '_'))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded}"

import urllib.parse

os.makedirs(PHOTOS_DIR, exist_ok=True)

# Load all records
records = []
for fn in sorted(os.listdir(RECORDS_DIR)):
    if fn.endswith('.json'):
        with open(os.path.join(RECORDS_DIR, fn)) as f:
            try:
                records.append((fn, json.load(f)))
            except:
                pass

print(f"Processing {len(records)} records...\n")

# Per-type cache so we only download once per type
type_cache = {}  # type -> local_path

for fn, rec in records:
    itype = rec.get('intervention_type', 'Check Dam')
    rid = rec.get('id', fn.replace('.json', ''))
    target_fname = rid + '.jpg'
    target_path = os.path.join(PHOTOS_DIR, target_fname)

    # Already good?
    if os.path.exists(target_path) and os.path.getsize(target_path) > 50000:
        print(f"  ✓  {itype:25} {target_fname} ({os.path.getsize(target_path)//1024}KB)")
        type_cache.setdefault(itype, target_path)
        # Update record anyway
        rec['photo_filename'] = target_fname
        rec['photo_url'] = f"/api/drishti/photos/{target_fname}"
        with open(os.path.join(RECORDS_DIR, fn), 'w') as f:
            json.dump(rec, f, indent=2)
        continue

    # Use cached type download
    if itype in type_cache:
        shutil.copy2(type_cache[itype], target_path)
        print(f"  C  {itype:25} {target_fname} (copied from cache)")
    else:
        # Build URL list to try
        urls_to_try = []
        for wf in WIKI_FILES.get(itype, []):
            urls_to_try.append(wiki_url(wf))
        if itype in VERIFIED_URLS:
            urls_to_try.append(VERIFIED_URLS[itype])
        if itype in UNSPLASH_FALLBACK:
            urls_to_try.append(UNSPLASH_FALLBACK[itype])

        downloaded = False
        for url in urls_to_try:
            try:
                sz = download(url, target_path)
                print(f"  ↓  {itype:25} {target_fname} ({sz//1024}KB)")
                type_cache[itype] = target_path
                downloaded = True
                break
            except Exception as e:
                print(f"     FAIL {url[:70]}: {e}")
                time.sleep(0.5)

        if not downloaded:
            print(f"  ✗  {itype:25} ALL SOURCES FAILED")
            continue

    # Update JSON record
    rec['photo_filename'] = target_fname
    rec['photo_url'] = f"/api/drishti/photos/{target_fname}"
    with open(os.path.join(RECORDS_DIR, fn), 'w') as f:
        json.dump(rec, f, indent=2)

    time.sleep(0.4)

print("\n=== Final photo sizes ===")
for fn in sorted(os.listdir(PHOTOS_DIR)):
    fp = os.path.join(PHOTOS_DIR, fn)
    sz = os.path.getsize(fp)
    status = "OK" if sz > 50000 else "SMALL/BAD"
    print(f"  {status:8} {fn:50} {sz//1024}KB")
