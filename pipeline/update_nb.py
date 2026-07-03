import json

with open(r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb', 'r') as f:
    nb = json.load(f)

# The source code is in the second cell
source = nb['cells'][1]['source']

new_source = []
for line in source:
    if "b64_data =" in line:
        continue # remove b64_data
    if "f.write(base64.b64decode(b64_data))" in line:
        continue
    if "with open(img_path, 'wb') as f:" in line:
        continue
    if "img_path = '/kaggle/working/page_20.png'" in line:
        new_source.append("img_path = '/kaggle/input/ielts-13-sample-pages/page_20.png'\n")
        continue
    if "hf_hub_download(" in line:
        new_source.append("model_path = hf_hub_download(repo_id=\"juliozhao/DocLayout-YOLO-DocStructBench\", filename=\"doclayout_yolo_docstructbench_imgsz1024.pt\")\n")
        continue
    new_source.append(line)

nb['cells'][1]['source'] = new_source

with open(r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb', 'w') as f:
    json.dump(nb, f, indent=2)

print("Notebook updated!")
