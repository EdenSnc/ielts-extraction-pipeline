"""
rebuild_vlm_nb.py
Generate vlm_interpretation.ipynb notebook for running Phase 4 on Kaggle.
Includes diagnostic path listing.
"""
import json
import os

NB_PATH = r'C:\Users\Admin\Documents\IELTS-PDFS\vlm_pipeline\vlm_interpretation.ipynb'
META_PATH = r'C:\Users\Admin\Documents\IELTS-PDFS\vlm_pipeline\kernel-metadata.json'

os.makedirs(os.path.dirname(NB_PATH), exist_ok=True)

cell0_source = "!pip install -q transformers accelerate torchvision qwen-vl-utils\n"

cell1_source = '''import os
import json
import glob
import torch
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

print("--- DIAGNOSTIC PATH LISTING ---")
input_root = "/kaggle/input"
print("Root /kaggle/input contents:")
print(os.listdir(input_root))
for folder in os.listdir(input_root):
    path = os.path.join(input_root, folder)
    if os.path.isdir(path):
        print(f"Subfolder {folder} contents:")
        print(os.listdir(path))
        # Look recursively inside
        for sub in os.listdir(path):
            sub_path = os.path.join(path, sub)
            if os.path.isdir(sub_path):
                print(f"  Sub-subfolder {sub} contents:")
                print(os.listdir(sub_path))
print("--------------------------------")

INPUT_DIR = "/kaggle/input/ielts-13-crops-v1"
# Let's search dynamically for manifest.json if path is different
candidates = glob.glob("/kaggle/input/**/manifest.json", recursive=True)
if candidates:
    MANIFEST_PATH = candidates[0]
    INPUT_DIR = os.path.dirname(MANIFEST_PATH)
    print(f"Found manifest.json dynamically at: {MANIFEST_PATH}")
    print(f"Set INPUT_DIR to: {INPUT_DIR}")
else:
    MANIFEST_PATH = os.path.join(INPUT_DIR, "manifest.json")
    print(f"Fallback to default MANIFEST_PATH: {MANIFEST_PATH}")

print("Loading Qwen2-VL-2B-Instruct...")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-2B-Instruct", torch_dtype="auto", device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
print("Model loaded successfully!")

# Ensure manifest exists
if not os.path.exists(MANIFEST_PATH):
    raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    crops = json.load(f)

def run_vlm(image_path, prompt):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": prompt}
            ]
        }
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt"
    )
    inputs = inputs.to("cuda")
    
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=1536)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
    return output_text.strip()

def validate_structured_data(asset_type, structured_data, alt_text=""):
    """Returns (is_valid, reason) — flags known failure modes for human review."""
    if not isinstance(structured_data, dict):
        return False, "structured_data is not a dict"
    if asset_type in ("flowchart", "process_diagram"):
        steps = structured_data.get("steps", [])
        if not steps:
            return False, "steps list is empty"
        if len(steps) == 1 and "step" in alt_text.lower() and alt_text.count("step") > 2:
            return False, f"only 1 step extracted but alt_text mentions multiple steps"
        for step in steps:
            if step.get("label", "").strip() in ("", "Step Description"):
                return False, f"step {step.get('id')} has placeholder label"
    elif asset_type == "map":
        labels = structured_data.get("labels", [])
        if not labels:
            return False, "labels list is empty"
        valid_locations = {
            "top-left", "top-center", "top-right",
            "center-left", "center", "center-right",
            "bottom-left", "bottom-center", "bottom-right"
        }
        for lbl in labels:
            loc = lbl.get("approx_location", "")
            if "|" in loc or loc.lower() not in valid_locations:
                return False, f"invalid approx_location value: {repr(loc)}"
    elif asset_type in ("bar_chart", "line_graph", "pie_chart"):
        series = structured_data.get("series", [])
        if not series:
            return False, "series list is empty"
        for s in series:
            if s.get("label", "").strip() in ("", "Series Name"):
                return False, f"series has placeholder label"
    return True, "ok"

results = []

for item in crops:
    crop_file = item["crop_filename"]
    img_path = os.path.join(INPUT_DIR, crop_file)
    print(f"\\nInterpreting crop: {crop_file} (Page {item['page']}, Layout Label: {item['label']})")
    
    if not os.path.exists(img_path):
        print(f"Error: image {img_path} not found.")
        continue
        
    yolo_label = item["label"]
    
    # 1. Determine specific asset_type
    if yolo_label == "table":
        asset_type = "table"
    else:
        # It's a figure, ask VLM to classify
        class_prompt = (
            "Classify this visual image into one of these exact types: "
            '"bar_chart", "line_graph", "pie_chart", "flowchart", "process_diagram", "map", "other_image". '
            "Output only the classification name without any other text or punctuation."
        )
        raw_class = run_vlm(img_path, class_prompt).lower().strip()
        print(f"VLM raw classification: {raw_class}")
        
        # Normalize
        asset_type = "other_image"
        for t in ["bar_chart", "line_graph", "pie_chart", "flowchart", "process_diagram", "map"]:
            if t in raw_class or t.replace("_", "") in raw_class:
                asset_type = t
                break
                
    print(f"Classified asset_type: {asset_type}")
    
    # 2. Alt Text description
    alt_prompt = (
        "Generate a detailed alt text description for this image, describing the chart or diagram. "
        "Include title, labels, keys, axes, and general trends or steps shown."
    )
    alt_text = run_vlm(img_path, alt_prompt)
    print(f"VLM Alt Text: {alt_text[:100]}...")
    
    # 3. Extract structured data
    structured_data = None
    if asset_type == "table":
        struct_prompt = (
            "Extract the table structure from this image. Return a JSON object with two fields: "
            '"columns" (an array of column headers) and "rows" (an array of rows, where each row is an array of cell values). '
            "Provide only valid JSON. Do not wrap in markdown code blocks."
        )
        raw_struct = run_vlm(img_path, struct_prompt)
        try:
            # Clean possible markdown wrap
            cleaned = raw_struct.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(cleaned)
        except Exception as e:
            print(f"Error parsing table JSON: {e}. Raw: {raw_struct}")
            structured_data = {"raw_text": raw_struct}
            
    elif asset_type in ["bar_chart", "line_graph", "pie_chart"]:
        struct_prompt = (
            "Extract the data points from this chart. Return a JSON object matching this structure: "
            '{"series": [{"label": "Series Name", "points": [{"x": "X value", "y": "Y value"}]}]}. '
            "Provide only valid JSON. Do not wrap in markdown code blocks."
        )
        raw_struct = run_vlm(img_path, struct_prompt)
        try:
            cleaned = raw_struct.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(cleaned)
        except Exception as e:
            print(f"Error parsing chart JSON: {e}. Raw: {raw_struct}")
            structured_data = {"raw_text": raw_struct}
            
    elif asset_type in ["flowchart", "process_diagram"]:
        struct_prompt = (
            "Extract the steps from this diagram. Return a JSON object matching this structure: "
            '{"steps": [{"id": "step_1", "label": "Step Description", "next": ["step_2"]}]}. '
            "Provide only valid JSON. Do not wrap in markdown code blocks."
        )
        raw_struct = run_vlm(img_path, struct_prompt)
        try:
            cleaned = raw_struct.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(cleaned)
        except Exception as e:
            print(f"Error parsing flowchart JSON: {e}. Raw: {raw_struct}")
            structured_data = {"raw_text": raw_struct}
            
    elif asset_type == "map":
        struct_prompt = (
            "Extract every labelled location from this map. "
            "Return a JSON object with this structure: "
            '{"labels": [{"text": "City Hospital", "approx_location": "Center"}]}. '
            "For approx_location use ONLY one of these exact values: "
            "Top-Left, Top-Center, Top-Right, Center-Left, Center, Center-Right, Bottom-Left, Bottom-Center, Bottom-Right. "
            "Include ALL visible labels. Provide only valid JSON. Do not wrap in markdown code blocks."
        )
        raw_struct = run_vlm(img_path, struct_prompt)
        try:
            cleaned = raw_struct.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(cleaned)
        except Exception as e:
            print(f"Error parsing map JSON: {e}. Raw: {raw_struct}")
            structured_data = {"raw_text": raw_struct}

    is_valid, validation_reason = validate_structured_data(asset_type, structured_data, alt_text)
    if not is_valid:
        print(f"  WARNING: structured_data validation failed: {validation_reason}")

    results.append({
        "page": item["page"],
        "label": yolo_label,
        "asset_type": asset_type,
        "box": item["box"],
        "alt_text": alt_text,
        "structured_data": structured_data,
        "crop_filename": crop_file,
        "needs_review": not is_valid,
        "review_reason": validation_reason if not is_valid else None,
    })

# Save results
OUTPUT_DIR = "/kaggle/working"
out_path = os.path.join(OUTPUT_DIR, "vlm_interpretation_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Interpretation complete. Results saved to {out_path}")
'''

new_nb = {
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4,
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": cell0_source
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": cell1_source
        }
    ]
}

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(new_nb, f, indent=1)

print("VLM Notebook generated successfully with diagnostic paths!")
