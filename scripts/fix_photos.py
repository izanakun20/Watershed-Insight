# -*- coding: utf-8 -*-
"""Fix all small/broken photo files by re-downloading from Unsplash."""
import os, json, urllib.request, sys, time
sys.stdout.reconfigure(encoding='utf-8')

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"
HEADERS = {"User-Agent": "Mozilla/5.0 (SIH26015-Watershed)"}

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
    if len(data) < 40000:
        raise ValueError(f"Too small: {len(data)}")
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


# Build record -> intervention_type map
rtype = {}
for fn in os.listdir(RECORDS_DIR):
    if fn.endswith(".json"):
        rec = json.load(open(os.path.join(RECORDS_DIR, fn)))
        rid = rec.get("id", fn.replace(".json", ""))
        rtype[rid] = rec.get("intervention_type", "Check Dam")

# Find bad jpgs
bad = []
for f in os.listdir(PHOTOS_DIR):
    if f.endswith(".jpg"):
        fp = os.path.join(PHOTOS_DIR, f)
        if os.path.getsize(fp) < 40000:
            bad.append((f, fp))

print(f"Fixing {len(bad)} bad/small JPG files...")

for fname, fpath in bad:
    rid = fname.replace(".jpg", "")
    itype = rtype.get(rid, "Check Dam")
    url = UNSPLASH.get(itype, DEFAULT)
    try:
        sz = download(url, fpath)
        kb = sz // 1024
        print(f"FIXED  {itype:25}  {fname[:20]}  {kb}KB")
    except Exception as e:
        print(f"ERR    {fname}: {e}")
    time.sleep(0.3)

print("\nFinal state:")
for f in sorted(os.listdir(PHOTOS_DIR)):
    if f.endswith(".jpg"):
        fp = os.path.join(PHOTOS_DIR, f)
        sz = os.path.getsize(fp)
        status = "OK " if sz > 40000 else "BAD"
        kb = sz // 1024
        print(f"  {status}  {f:50}  {kb}KB")
