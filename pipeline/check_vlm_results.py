import json

path = r"C:\Users\Admin\Documents\IELTS-PDFS\vlm_pipeline\vlm_interpretation_results.json"

with open(path, encoding="utf-8") as f:
    data = json.load(f)

for r in data:
    page = r.get("page")
    asset_type = r.get("asset_type")
    sd = r.get("structured_data")
    needs_review = r.get("needs_review", False)
    review_reason = r.get("review_reason")
    if asset_type in ("flowchart", "process_diagram"):
        steps = sd.get("steps", []) if isinstance(sd, dict) else []
        print(f"Page {page} ({asset_type}): {len(steps)} steps | needs_review={needs_review}")
        for s in steps:
            print(f"    {s.get('id')}: {s.get('label')}")
    elif asset_type == "map":
        labels = sd.get("labels", []) if isinstance(sd, dict) else []
        print(f"Page {page} ({asset_type}): {len(labels)} labels | needs_review={needs_review}")
        for l in labels:
            print(f"    {l.get('text')!r} -> {l.get('approx_location')!r}")
    else:
        print(f"Page {page} ({asset_type}): structured_data present | needs_review={needs_review}")
    if needs_review:
        print(f"  *** NEEDS REVIEW: {review_reason}")
import json

path = r"C:\Users\Admin\Documents\IELTS-PDFS\vlm_pipeline\vlm_interpretation_results.json"

with open(path, encoding="utf-8") as f:
    data = json.load(f)

for r in data:
    page = r.get("page")
    asset_type = r.get("asset_type")
    sd = r.get("structured_data")
    if asset_type in ("flowchart", "process_diagram"):
        steps = sd.get("steps", []) if isinstance(sd, dict) else []
        print(f"Page {page} ({asset_type}): {len(steps)} steps")
        for s in steps:
            print(f"    {s.get('id')}: {s.get('label')}")
    elif asset_type == "map":
        labels = sd.get("labels", []) if isinstance(sd, dict) else []
        print(f"Page {page} ({asset_type}): {len(labels)} labels")
        for l in labels:
            print(f"    {l.get('text')!r} -> {l.get('approx_location')!r}")
    else:
        print(f"Page {page} ({asset_type}): OK, structured_data present")
