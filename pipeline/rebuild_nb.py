"""
Rebuild kaggle_pipeline.ipynb to test layout detection on multiple pages with IoU deduplication.
This version uses the mounted Kaggle Dataset for full-resolution page images.
"""
import json
import os

NB_PATH = r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb'

cell0_source = "!pip install -q doclayout_yolo==0.0.4 huggingface_hub\n"

cell1_source = '''import os
import json
from PIL import Image, ImageDraw
from huggingface_hub import hf_hub_download
from doclayout_yolo import YOLOv10

INPUT_DIR = '/kaggle/input/ielts-13-sample-pages-v1'
OUTPUT_DIR = '/kaggle/working/layout_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

model_path = hf_hub_download(
    repo_id='juliozhao/DocLayout-YOLO-DocStructBench',
    filename='doclayout_yolo_docstructbench_imgsz1024.pt'
)
model = YOLOv10(model_path)

print("--- FULL CLASS LIST ---")
print(model.names)
print("-----------------------")

def get_area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])

def get_intersection_area(box1, box2):
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)

def get_iou(box1, box2):
    inter = get_intersection_area(box1, box2)
    area1 = get_area(box1)
    area2 = get_area(box2)
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0

def get_containment(box1, box2):
    inter = get_intersection_area(box1, box2)
    area1 = get_area(box1)
    return inter / area1 if area1 > 0 else 0.0

def is_adjacent_or_overlapping(caption_box, visual_box, max_dist=120):
    if get_intersection_area(caption_box, visual_box) > 0:
        return True
    dist_v1 = caption_box[1] - visual_box[3]
    dist_v2 = visual_box[1] - caption_box[3]
    h_overlap = max(0, min(caption_box[2], visual_box[2]) - max(caption_box[0], visual_box[0]))
    if h_overlap > 0 or (caption_box[0] < visual_box[2] + 50 and visual_box[0] < caption_box[2] + 50):
        if (0 <= dist_v1 <= max_dist) or (0 <= dist_v2 <= max_dist):
            return True
    return False

all_results = []
pages = [15, 19, 20, 30, 52]

for pg in pages:
    print(f"\\nProcessing Page {pg}...")
    img_path = os.path.join(INPUT_DIR, f'page_{pg}.png')
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found!")
        continue
        
    res = model.predict(img_path, imgsz=1024, conf=0.25, device='cuda', verbose=False)[0]
    
    # Phase 1: Filter raw detections into candidates based on thresholds
    high_conf_visuals = []
    captions = []
    others = []
    
    for box in res.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        
        box_dict = {'label': label, 'box': [x1, y1, x2, y2], 'confidence': conf}
        
        if label in ['figure', 'table']:
            if conf >= 0.50:
                high_conf_visuals.append(box_dict)
        elif label in ['figure_caption', 'table_caption']:
            if conf >= 0.25: # relaxed threshold for caption candidates
                captions.append(box_dict)
        else:
            if conf >= 0.30: # keep standard threshold at 0.30 to detect question text!
                others.append(box_dict)
                
    # Phase 2: Validate captions with low confidence (0.25 - 0.50)
    valid_captions = []
    for cap in captions:
        if cap['confidence'] >= 0.50:
            valid_captions.append(cap)
        else:
            is_valid = False
            for vis in high_conf_visuals:
                expected_vis_type = 'figure' if cap['label'] == 'figure_caption' else 'table'
                if vis['label'] == expected_vis_type:
                    if is_adjacent_or_overlapping(cap['box'], vis['box'], max_dist=120):
                        is_valid = True
                        break
            if is_valid:
                valid_captions.append(cap)
                
    # Combine kept boxes
    raw_bboxes = high_conf_visuals + valid_captions + others
    
    # Phase 3: Same-class containment deduplication (drop strictly larger outer grouping boxes)
    to_drop = set()
    for i in range(len(raw_bboxes)):
        for j in range(len(raw_bboxes)):
            if i == j: continue
            if raw_bboxes[i]['label'] != raw_bboxes[j]['label']: continue
            
            area_i = get_area(raw_bboxes[i]['box'])
            area_j = get_area(raw_bboxes[j]['box'])
            inter = get_intersection_area(raw_bboxes[i]['box'], raw_bboxes[j]['box'])
            
            if area_i > 0 and inter / area_i > 0.90:
                if area_j > 0 and inter / area_j > 0.90:
                    if raw_bboxes[i]['confidence'] >= raw_bboxes[j]['confidence']:
                        to_drop.add(j)
                    else:
                        to_drop.add(i)
                else:
                    # box j is strictly larger (the grouping/outer box), drop it
                    to_drop.add(j)
                    
    # Phase 4: Cross-class deduplication (abandon vs text/caption, figure/table vs text/title)
    for i in range(len(raw_bboxes)):
        if i in to_drop: continue
        for j in range(len(raw_bboxes)):
            if j in to_drop or i == j: continue
            
            label_i = raw_bboxes[i]['label']
            label_j = raw_bboxes[j]['label']
            if label_i == label_j: continue
            
            box_i = raw_bboxes[i]['box']
            box_j = raw_bboxes[j]['box']
            
            iou = get_iou(box_i, box_j)
            cont_i = get_containment(box_i, box_j) # box_i inside box_j
            cont_j = get_containment(box_j, box_i) # box_j inside box_i
            
            # If they overlap significantly
            if iou > 0.50 or cont_i > 0.80 or cont_j > 0.80:
                # Rule 1: abandon vs others -> abandon wins
                if label_i == 'abandon' and label_j in ['title', 'plain text', 'figure_caption', 'table_caption']:
                    to_drop.add(j)
                elif label_j == 'abandon' and label_i in ['title', 'plain text', 'figure_caption', 'table_caption']:
                    to_drop.add(i)
                # Rule 2: figure/table vs plain text/title -> figure/table wins
                elif label_i in ['figure', 'table'] and label_j in ['plain text', 'title']:
                    to_drop.add(j)
                elif label_j in ['figure', 'table'] and label_i in ['plain text', 'title']:
                    to_drop.add(i)
                    
    final_bboxes = [b for idx, b in enumerate(raw_bboxes) if idx not in to_drop]
    
    print(f"Page {pg}: Found {len(raw_bboxes)} raw boxes, reduced to {len(final_bboxes)} after dedup.")
    all_results.append({'page': pg, 'filename': f'page_{pg}.png', 'bboxes': final_bboxes})
    
    # Draw annotated image
    img = Image.open(img_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    for b in final_bboxes:
        x1, y1, x2, y2 = b['box']
        label = b['label']
        conf = b['confidence']
        draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
        draw.text((x1, max(0, y1 - 15)), f'{label} {conf:.2f}', fill='red')
        
    out_img_path = os.path.join(OUTPUT_DIR, f'page_{pg}.png')
    img.save(out_img_path)

with open(os.path.join(OUTPUT_DIR, 'layout_data.json'), 'w') as f:
    json.dump(all_results, f, indent=2)

print("\\nDone all pages!")
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

print("Notebook generated successfully!")
