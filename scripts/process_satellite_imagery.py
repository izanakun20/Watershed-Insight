"""
Satellite Image Processing for Watershed Condition Analysis (SIH 26015)

This script demonstrates how to derive key indicators from Sentinel-2
multispectral imagery using standard Python remote sensing libraries.

Note: Run this on actual Sentinel-2 L2A (Bottom of Atmosphere) products
downloaded from Copernicus Data Space or Bhoonidhi.

Dependencies:
    pip install rasterio numpy matplotlib
"""

import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def calculate_ndvi(red_band_path, nir_band_path, output_path=None):
    """
    Calculate Normalized Difference Vegetation Index (NDVI).
    NDVI = (NIR - RED) / (NIR + RED)
    Sentinel-2: RED = Band 4 (B04), NIR = Band 8 (B08)
    """
    print(f"Calculating NDVI from {red_band_path} and {nir_band_path}...")
    
    with rasterio.open(red_band_path) as red_src, rasterio.open(nir_band_path) as nir_src:
        red = red_src.read(1).astype('float32')
        nir = nir_src.read(1).astype('float32')
        
        # Avoid division by zero
        np.seterr(divide='ignore', invalid='ignore')
        
        ndvi = np.where(
            (nir + red) == 0.,
            0,
            (nir - red) / (nir + red)
        )
        
        # Save output if path is provided
        if output_path:
            meta = red_src.meta
            meta.update(dtype=rasterio.float32, count=1)
            
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(ndvi, 1)
            print(f"NDVI saved to {output_path}")
            
        return ndvi, red_src.meta

def calculate_ndwi(green_band_path, nir_band_path, output_path=None):
    """
    Calculate Normalized Difference Water Index (NDWI) - McFeeters (1996).
    Good for detecting open water bodies.
    NDWI = (GREEN - NIR) / (GREEN + NIR)
    Sentinel-2: GREEN = Band 3 (B03), NIR = Band 8 (B08)
    """
    print(f"Calculating NDWI from {green_band_path} and {nir_band_path}...")
    
    with rasterio.open(green_band_path) as green_src, rasterio.open(nir_band_path) as nir_src:
        green = green_src.read(1).astype('float32')
        nir = nir_src.read(1).astype('float32')
        
        np.seterr(divide='ignore', invalid='ignore')
        
        ndwi = np.where(
            (green + nir) == 0.,
            0,
            (green - nir) / (green + nir)
        )
        
        if output_path:
            meta = green_src.meta
            meta.update(dtype=rasterio.float32, count=1)
            
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(ndwi, 1)
            print(f"NDWI saved to {output_path}")
            
        return ndwi, green_src.meta

def extract_water_mask(ndwi_array, threshold=0.1):
    """
    Create a binary mask of water bodies using an NDWI threshold.
    Values > threshold are considered water.
    """
    # Create mask (1 for water, 0 for non-water)
    water_mask = np.where(ndwi_array > threshold, 1, 0).astype('uint8')
    return water_mask

def plot_indices(ndvi, ndwi, water_mask):
    """Plot the results for visual inspection."""
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    
    im1 = ax1.imshow(ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
    ax1.set_title('NDVI (Vegetation)')
    plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    
    im2 = ax2.imshow(ndwi, cmap='Blues', vmin=-1, vmax=1)
    ax2.set_title('NDWI (Water)')
    plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    
    im3 = ax3.imshow(water_mask, cmap='binary')
    ax3.set_title(f'Water Mask (NDWI > threshold)')
    
    plt.tight_layout()
    plt.show()

# Example usage instructions:
"""
# 1. Download Sentinel-2 L2A product for your AOI (e.g., tile 44PNT for Prakasam)
# 2. Extract the SAFE folder
# 3. Locate the 10m resolution bands in the GRANULE/<granule_id>/IMG_DATA/R10m/ folder

# Define paths to your downloaded bands
b03_path = "path/to/T44PNT_20240101T051234_B03_10m.jp2" # Green
b04_path = "path/to/T44PNT_20240101T051234_B04_10m.jp2" # Red
b08_path = "path/to/T44PNT_20240101T051234_B08_10m.jp2" # NIR

# Run analysis
ndvi, meta = calculate_ndvi(b04_path, b08_path, "processed_data/ndvi.tif")
ndwi, meta = calculate_ndwi(b03_path, b08_path, "processed_data/ndwi.tif")
water_mask = extract_water_mask(ndwi, threshold=0.1)

# Visualize
plot_indices(ndvi, ndwi, water_mask)
"""
