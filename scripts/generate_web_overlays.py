"""
Generate all web overlay PNGs for the frontend map.
Produces overlays for: NDVI, NDVI Change, NDWI, Water Mask, Water Change, Slope.
Also generates a legend-ready bounds.json.
"""
import os
import json
import numpy as np
import rasterio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

OUTPUT_DIR = "processed_data/web"

def generate_overlay(tif_path, png_path, cmap_name, vmin=None, vmax=None, nodata_val=None, discrete_colors=None):
    """Render a GeoTIFF as a transparent PNG for Leaflet overlay."""
    if not os.path.exists(tif_path):
        print(f"  Skipping {tif_path}, not found.")
        return None

    with rasterio.open(tif_path) as src:
        data = src.read(1)
        bounds = src.bounds

    # Create nodata mask
    nodata = nodata_val if nodata_val is not None else None
    mask = np.isnan(data)
    if nodata is not None and not np.isnan(nodata):
        mask = mask | (data == nodata)

    if discrete_colors:
        # Discrete colormap for binary/categorical data
        h, w = data.shape
        rgba_img = np.zeros((h, w, 4), dtype=np.float32)
        for val, color in discrete_colors.items():
            match = (data == val) & ~mask
            rgba_img[match] = color
        rgba_img[mask] = [0, 0, 0, 0]
    else:
        # Continuous colormap
        valid = data[~mask]
        d_min = np.nanmin(valid) if vmin is None else vmin
        d_max = np.nanmax(valid) if vmax is None else vmax
        if d_max == d_min:
            d_max += 1e-5

        norm_data = np.clip((data - d_min) / (d_max - d_min), 0, 1)
        cmap = plt.get_cmap(cmap_name)
        rgba_img = cmap(norm_data)
        rgba_img[mask, 3] = 0.0

    plt.imsave(png_path, rgba_img)
    leaflet_bounds = [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
    print(f"  Generated {png_path}")
    return leaflet_bounds


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_bounds = {}

    print("Generating web overlays...")

    # 1. Current NDVI (2026)
    b = generate_overlay(
        "processed_data/ndvi_clipped.tif",
        f"{OUTPUT_DIR}/ndvi.png",
        "RdYlGn", vmin=-0.2, vmax=0.8
    )
    if b: all_bounds["ndvi"] = b

    # 2. NDVI Change
    b = generate_overlay(
        "processed_data/ndvi_change_2025_2026.tif",
        f"{OUTPUT_DIR}/ndvi_change.png",
        "RdBu", vmin=-0.3, vmax=0.3
    )
    if b: all_bounds["ndvi_change"] = b

    # 3. NDWI (2026)
    b = generate_overlay(
        "processed_data/ndwi_clipped.tif",
        f"{OUTPUT_DIR}/ndwi.png",
        "YlGnBu", vmin=-0.3, vmax=0.5
    )
    if b: all_bounds["ndwi"] = b

    # 4. Water Mask (2026) - discrete binary
    b = generate_overlay(
        "processed_data/water_mask_clipped.tif",
        f"{OUTPUT_DIR}/water_mask.png",
        None,
        discrete_colors={
            0: [0, 0, 0, 0],           # No water = transparent
            1: [0.2, 0.5, 0.9, 0.7],   # Water = blue
        }
    )
    if b: all_bounds["water_mask"] = b

    # 5. Water Change - discrete ternary
    b = generate_overlay(
        "processed_data/water_change_2025_2026.tif",
        f"{OUTPUT_DIR}/water_change.png",
        None,
        discrete_colors={
            -1: [0.9, 0.2, 0.2, 0.7],  # Water loss = red
            0:  [0, 0, 0, 0],           # No change = transparent
            1:  [0.2, 0.5, 0.9, 0.7],   # New water = blue
        }
    )
    if b: all_bounds["water_change"] = b

    # 6. Slope
    b = generate_overlay(
        "processed_data/cartodem_slope.tif",
        f"{OUTPUT_DIR}/slope.png",
        "plasma", vmin=0, vmax=20, nodata_val=-9999
    )
    if b: all_bounds["slope"] = b

    # Save bounds
    with open(f"{OUTPUT_DIR}/bounds.json", "w") as f:
        json.dump(all_bounds, f, indent=2)
    print(f"\nSaved bounds.json with {len(all_bounds)} layers.")
    print("Done.")

if __name__ == "__main__":
    main()
