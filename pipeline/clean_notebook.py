import json

file_path = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb"
with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Clear outputs and attachments, and huge base64 strings in code cells
for cell in nb.get("cells", []):
    # clear outputs
    if "outputs" in cell:
        cell["outputs"] = []
    
    # clear execution counts
    if "execution_count" in cell:
        cell["execution_count"] = None
        
    # clear attachments
    if "attachments" in cell:
        cell["attachments"] = {}
        
    # truncate giant string assignments in source
    if cell.get("cell_type") == "code":
        new_source = []
        for line in cell.get("source", []):
            if len(line) > 5000:
                print("Found huge line! Truncating...")
                # It might be `b64_string = "..."`
                if "=" in line:
                    prefix = line.split("=")[0]
                    new_source.append(prefix + "= \"\"\n")
                else:
                    new_source.append("# TRUNCATED\n")
            else:
                new_source.append(line)
        cell["source"] = new_source

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(nb, f)

import os
print("New size:", os.path.getsize(file_path))
