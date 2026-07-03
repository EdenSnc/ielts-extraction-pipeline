"""
Rebuild kaggle_pipeline.ipynb to test layout detection on multiple pages with IoU deduplication.
"""
import json
import os
import fitz
import base64

NB_PATH = r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb'
PDF_PATH = r'C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS Academic\13.PDF'

# Extract pages 20 (questions), 30 (map), 52 (chart)
doc = fitz.open(PDF_PATH)
pages_b64 = {}
for pg in [20, 30, 52]:
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(1.1, 1.1)) # 1.1x scaling to keep total b64 < 1MB
    img_bytes = pix.tobytes('png')
    pages_b64[str(pg)] = base64.b64encode(img_bytes).decode('ascii')

cell0_source = "!pip install -q doclayout_yolo==0.0.4 huggingface_hub\n"

cell1_source = f'''import os
import base64
import json
from PIL import Image, ImageDraw
from huggingface_hub import hf_hub_download
from doclayout_yolo import YOLOv10

OUTPUT_DIR = '/kaggle/working/layout_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

pages_b64 = {json.dumps(pages_b64)}

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

all_results = []

for pg_str, b64_data in pages_b64.items():
    pg = int(pg_str)
    print(f"\\nProcessing Page {{pg}}...")
    img_path = f'/kaggle/working/page_{{pg}}.png'
    with open(img_path, 'wb') as f:
        f.write(base64.b64decode(b64_data))
        
    res = model.predict(img_path, imgsz=1024, conf=0.3, device='cuda', verbose=False)[0]
    
    raw_bboxes = []
    for box in res.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        raw_bboxes.append({{'label': label, 'box': [x1, y1, x2, y2], 'confidence': conf}})
        
    # IoU / Containment Deduplication
    to_drop = set()
    for i in range(len(raw_bboxes)):
        for j in range(len(raw_bboxes)):
            if i == j: continue
            if raw_bboxes[i]['label'] != raw_bboxes[j]['label']: continue
            
            area_i = get_area(raw_bboxes[i]['box'])
            area_j = get_area(raw_bboxes[j]['box'])
            inter = get_intersection_area(raw_bboxes[i]['box'], raw_bboxes[j]['box'])
            
            if area_i > 0 and inter / area_i > 0.90:
                # box i is >90% contained in box j
                if area_j > 0 and inter / area_j > 0.90:
                    # nearly identical, keep highest confidence
                    if raw_bboxes[i]['confidence'] >= raw_bboxes[j]['confidence']:
                        to_drop.add(j)
                    else:
                        to_drop.add(i)
                else:
                    # box j is strictly larger (the grouping/outer box)
                    to_drop.add(j)
                    
    final_bboxes = [b for idx, b in enumerate(raw_bboxes) if idx not in to_drop]
    
    print(f"Page {{pg}}: Found {{len(raw_bboxes)}} raw boxes, reduced to {{len(final_bboxes)}} after containment dedup.")
    all_results.append({{'page': pg, 'filename': f'page_{{pg}}.png', 'bboxes': final_bboxes}})
    
    # Draw annotated image
    img = Image.open(img_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    for b in final_bboxes:
        x1, y1, x2, y2 = b['box']
        label = b['label']
        conf = b['confidence']
        draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
        draw.text((x1, max(0, y1 - 15)), f'{{label}} {{conf:.2f}}', fill='red')
        
    out_img_path = os.path.join(OUTPUT_DIR, f'page_{{pg}}.png')
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
