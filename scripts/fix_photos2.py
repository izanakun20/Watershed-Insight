# -*- coding: utf-8 -*-
"""Fix remaining 11 bad Check Dam photos by copying from a good existing file."""
import os, json, shutil, urllib.request

RECORDS_DIR = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\records"
PHOTOS_DIR  = r"c:\Users\siddh\.gemini\antigravity\scratch\sih26015\mock_drishti_data\photos"

# Use an already-good check dam photo as the source
# 5eb7d8e3 is 48KB OK, 883ecf7b is 48KB OK -- use one as donor
DONOR = os.path.join(PHOTOS_DIR, "5eb7d8e3-5006-41fb-924d-2abc1482d6c4.jpg")

# List all bad jpgs
bad = []
for f in os.listdir(PHOTOS_DIR):
    if f.endswith(".jpg"):
        fp = os.path.join(PHOTOS_DIR, f)
        if os.path.getsize(fp) < 40000:
            bad.append(fp)

print(f"Copying donor ({os.path.getsize(DONOR)//1024}KB) to {len(bad)} bad files...")

for fp in bad:
    shutil.copy2(DONOR, fp)
    print(f"  FIXED  {os.path.basename(fp)}  -> {os.path.getsize(fp)//1024}KB")

print("\nFinal:")
for f in sorted(os.listdir(PHOTOS_DIR)):
    if f.endswith(".jpg"):
        fp = os.path.join(PHOTOS_DIR, f)
        sz = os.path.getsize(fp)
        print(f"  {'OK ' if sz>40000 else 'BAD'}  {f:50}  {sz//1024}KB")
