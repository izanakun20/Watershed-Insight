# -*- coding: utf-8 -*-
import os, json, shutil, time, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"
HEADERS = {"User-Agent": "Mozilla/5.0 (SIH26015-Watershed; educational)"}

# Free Unsplash photos by intervention type (no API key needed for direct URLs)
UNSPLASH = {
    "Check Dam":           "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&q=80",
    "Stop Dam":            "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80",
    "Farm Pond":           "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80",
    "Trenching":           "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80",
    "Afforestation":       "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800&q=80",
    "Contour Bunding":     "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
    "Gully Plugs":         "https://images.unsplash.com/photo-1509622905150-fa66d3906e09?w=800&q=80",
    "Terracing":           "https://images.unsplash.com/photo-1596484552834-6a58f850e0a1?w=800&q=80",
    "Pasture Development": "https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=800&q=80",
    "Agro-forestry":       "https://images.unsplash.com/photo-1518314916381-77a37c2a49ae?w=800&q=80",
    "Percolation Tank":    "https://images.unsplash.com/photo-1470770903676-69b98201ea1c?w=800&q=80",
}
DEFAULT = "https://images.unsplash.com/photo-1470770903676-69b98201ea1c?w=800&q=80"


def download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    if len(data) < 8000:
        raise ValueError(f"Too small: {len(data)} bytes")
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


os.makedirs(PHOTOS_DIR, exist_ok=True)

records = []
for fn in sorted(os.listdir(RECORDS_DIR)):
    if fn.endswith(".json"):
        try:
            with open(os.path.join(RECORDS_DIR, fn)) as f:
                records.append((fn, json.load(f)))
        except Exception:
            pass

print(f"Processing {len(records)} records...\n")

type_cache = {}

for fn, rec in records:
    itype = rec.get("intervention_type", "Check Dam")
    rid   = rec.get("id", fn.replace(".json", ""))
    tgt   = os.path.join(PHOTOS_DIR, rid + ".jpg")

    if os.path.exists(tgt) and os.path.getsize(tgt) > 50000:
        print(f"OK   {itype:25} {rid[:8]}...jpg  ({os.path.getsize(tgt)//1024}KB)")
        type_cache.setdefault(itype, tgt)
    elif itype in type_cache:
        shutil.copy2(type_cache[itype], tgt)
        print(f"COPY {itype:25} {rid[:8]}...jpg")
    else:
        url = UNSPLASH.get(itype, DEFAULT)
        try:
            sz = download(url, tgt)
            print(f"DL   {itype:25} {rid[:8]}...jpg  ({sz//1024}KB)  {url[:55]}")
            type_cache[itype] = tgt
        except Exception as e:
            print(f"ERR  {itype}: {e}")
            continue

    # Update the record JSON
    rec["photo_filename"] = rid + ".jpg"
    rec["photo_url"] = f"/api/drishti/photos/{rid}.jpg"
    with open(os.path.join(RECORDS_DIR, fn), "w") as f:
        json.dump(rec, f, indent=2)

    time.sleep(0.3)

print("\n=== Summary ===")
for fn in sorted(os.listdir(PHOTOS_DIR)):
    fp = os.path.join(PHOTOS_DIR, fn)
    sz = os.path.getsize(fp)
    flag = "OK " if sz > 50000 else "BAD"
    print(f"  {flag}  {fn:50}  {sz//1024}KB")
