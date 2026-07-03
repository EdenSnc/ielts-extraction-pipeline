import json

file_path = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb"
with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if "outputs" in cell:
        cell["outputs"] = []
    if "execution_count" in cell:
        cell["execution_count"] = None

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Outputs cleared.")
