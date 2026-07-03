import base64
import json

img_path = r'C:\Users\Admin\.gemini\antigravity-ide\brain\54874f8a-6f56-49f3-97bf-357538822b35\page_20.png'
with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

nb_path = r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb'
with open(nb_path, 'r') as f:
    nb = json.load(f)

source = []
source.append("import os\n")
source.append("import base64\n")
source.append("import json\n")
source.append("from PIL import Image, ImageDraw\n")
source.append("from huggingface_hub import hf_hub_download\n")
source.append("from ultralytics import YOLO\n\n")
source.append("OUTPUT_DIR = '/kaggle/working/layout_output'\n")
source.append("os.makedirs(OUTPUT_DIR, exist_ok=True)\n\n")
source.append(f"b64_data = '{b64}'\n")
source.append("img_path = '/kaggle/working/page_20.png'\n")
source.append("with open(img_path, 'wb') as f:\n")
source.append("    f.write(base64.b64decode(b64_data))\n\n")
source.append("model_path = hf_hub_download(repo_id='juliozhao/DocLayout-YOLO-DocStructBench', filename='doclayout_yolo_docstructbench_imgsz1024.pt')\n")
source.append("model = YOLO(model_path)\n\n")
source.append("res = model.predict(img_path, conf=0.3, save=False)[0]\n")
source.append("bboxes = []\n")
source.append("img = Image.open(img_path).convert('RGB')\n")
source.append("draw = ImageDraw.Draw(img)\n")
source.append("for box in res.boxes:\n")
source.append("    x1, y1, x2, y2 = box.xyxy[0].tolist()\n")
source.append("    conf = box.conf[0].item()\n")
source.append("    cls_id = int(box.cls[0].item())\n")
source.append("    label = model.names[cls_id]\n")
source.append("    bboxes.append({'label': label, 'box': [x1, y1, x2, y2], 'confidence': conf})\n")
source.append("    draw.rectangle([x1, y1, x2, y2], outline='red', width=3)\n")
source.append("    draw.text((x1, max(0, y1 - 15)), f'{label} {conf:.2f}', fill='red')\n\n")
source.append("out_img_path = os.path.join(OUTPUT_DIR, 'page_20.png')\n")
source.append("img.save(out_img_path)\n")
source.append("with open(os.path.join(OUTPUT_DIR, 'layout_data.json'), 'w') as f:\n")
source.append("    json.dump([{'filename': 'page_20.png', 'bboxes': bboxes}], f, indent=2)\n")
source.append("print('Done!')\n")

nb['cells'][1]['source'] = source

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=2)

print("Notebook generated with base64 data.")
