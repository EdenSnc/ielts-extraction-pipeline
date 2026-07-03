import json

file_path = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb"
with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb.get("cells", [])):
    source = cell.get("source", [])
    if isinstance(source, list):
        src_len = sum(len(x) for x in source)
        if src_len > 10000:
            print(f"Cell {idx} has length {src_len}")
    elif isinstance(source, str):
        if len(source) > 10000:
            print(f"Cell {idx} has length {len(source)}")
