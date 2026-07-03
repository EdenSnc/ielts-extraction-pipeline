import fitz
import os
import json

def run_smoke_test(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    
    print(f"Running smoke test on {pdf_path}...")
    
    document_record = {
        "document_id": "doc_13_pdf",
        "filename": os.path.basename(pdf_path),
        "book_type": "cambridge_academic",
        "subfolder": "Cambridge IELTS Academic",
        "is_digital": False,
        "page_count": len(doc),
        "visual_density_estimate": "medium",
        "page_boundary_anomaly_flag": False
    }
    
    modules = []
    visual_assets = []
    
    # Process page 20, 21 as sample
    for page_num in [20, 21]:
        page = doc[page_num]
        
        # Schema requires integer or null for printed_page_number
        label = page.get_label()
        try:
            printed_page_number = int(label) if label else page_num
        except ValueError:
            printed_page_number = None
            
        text_blocks = page.get_text("blocks")
        text_only = [b[4] for b in text_blocks if b[6] == 0]
        print(f"Extracted {len(text_only)} text blocks from page {page_num}.")
        
        passage_text = "\n\n".join(text_only)
        
        sections = [
            {
                "section_id": f"sec_13_{page_num}",
                "part_number": 1,
                "title": f"Sample Passage Page {page_num}",
                "instructions_text": "Read the text.",
                "passage_or_prompt_text": passage_text,
                "source_page_range": [page_num, page_num],
                "visual_asset_ids": [f"asset_p{page_num}_1"],
                "questions": []
            }
        ]
        
        modules.append({
            "module_id": f"mod_13_{page_num}_reading",
            "module_type": "reading",
            "sections": sections
        })
        
        visual_assets.append({
            "asset_id": f"asset_p{page_num}_1",
            "asset_type": "table" if page_num == 20 else "other_image",
            "document_id": "doc_13_pdf",
            "pdf_page_index": page_num,
            "printed_page_number": printed_page_number,
            "bbox": [100.0, 100.0, 500.0, 500.0],
            "image_path": f"assets/asset_p{page_num}_1.png",
            "linked_question_ids": [],
            "structured_data": None,
            "alt_text": "Mock visual asset",
            "provenance": {
                "extraction_method": "mock_layout_routing",
                "confidence_score": 0.0,
                "human_reviewed": False
            }
        })
    
    test_record = {
        "test_id": "test_13_1",
        "document_id": "doc_13_pdf",
        "test_label": "Cambridge IELTS 13, Test 1",
        "modules": modules
    }
    
    dataset = {
        "documents": [document_record],
        "tests": [test_record],
        "visual_assets": visual_assets
    }
    
    out_file = os.path.join(output_dir, "smoke_test_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Smoke test complete. Output saved to {out_file}")

if __name__ == "__main__":
    pdf_path = r"C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS Academic\13.PDF"
    out_dir = r"C:\Users\Admin\Documents\IELTS-PDFS\pipeline\smoke_test_output"
    run_smoke_test(pdf_path, out_dir)
