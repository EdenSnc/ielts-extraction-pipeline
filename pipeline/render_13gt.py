"""
render_13gt.py
Render all pages of 13gt.pdf at 150 DPI (target size ~1366x1899).
"""
import os
import fitz

pdf_path = r"C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS General Training\13gt.pdf"
out_dir = r"C:\Users\Admin\Documents\IELTS-PDFS\dataset_13gt\images"
os.makedirs(out_dir, exist_ok=True)

print(f"Opening {pdf_path}...")
doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")

# Render at 150 DPI
zoom = 150 / 72
mat = fitz.Matrix(zoom, zoom)

for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=mat)
    out_path = os.path.join(out_dir, f"page_{i}.png")
    pix.save(out_path)
    if i % 10 == 0 or i == len(doc) - 1:
        print(f"Rendered page {i}/{len(doc)-1} -> {out_path} (size={pix.width}x{pix.height})")

print("Rendering complete!")
