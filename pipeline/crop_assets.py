"""
crop_assets.py
Crop detected figures and tables from page images based on layout_data.json.
Saved to a local crops directory.
"""
import os
import json
from PIL import Image

from bbox_utils import pad_box

LAYOUT_JSON = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_output\layout_output\layout_data.json"
IMAGE_DIR = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\dataset_sample\images"
CROPS_DIR = r"C:\Users\Admin\Documents\IELTS-PDFS\crops"

os.makedirs(CROPS_DIR, exist_ok=True)

if not os.path.exists(LAYOUT_JSON):
    print(f"Error: {LAYOUT_JSON} does not exist.")
    exit(1)

with open(LAYOUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

crop_manifest = []

for page_item in data:
    page_num = page_item["page"]
    filename = page_item["filename"]
    img_path = os.path.join(IMAGE_DIR, filename)
    
    if not os.path.exists(img_path):
        print(f"Warning: Image {img_path} not found.")
        continue
        
    img = Image.open(img_path)
    
    for idx, bbox_item in enumerate(page_item.get("bboxes", [])):
        label = bbox_item["label"]
        if label not in ["figure", "table"]:
            continue
            
        box = bbox_item["box"] # [x1, y1, x2, y2] canonical detection coords
        conf = bbox_item["confidence"]
        
        # Crop with a fixed 15px margin, clamped to page bounds. `box` stays canonical.
        padded_box = pad_box(box, img.width, img.height)
        cropped_img = img.crop(tuple(padded_box))
        crop_filename = f"page_{page_num}_{label}_{idx}.png"
        crop_path = os.path.join(CROPS_DIR, crop_filename)
        cropped_img.save(crop_path)
        
        crop_manifest.append({
            "page": page_num,
            "label": label,
            "confidence": conf,
            "box": box,
            "padded_box": padded_box,
            "crop_filename": crop_filename
        })
        print(f"Saved crop: {crop_filename} size={cropped_img.size}")

manifest_path = os.path.join(CROPS_DIR, "manifest.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(crop_manifest, f, indent=2)

print(f"Cropped {len(crop_manifest)} assets and wrote manifest to {manifest_path}")
