import os
import subprocess
import fitz

def main():
    print("Testing Surya OCR locally...")
    
    # Render a single page to test
    pdf_path = r"C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS Academic\13.PDF"
    doc = fitz.open(pdf_path)
    page = doc[20]
    pix = page.get_pixmap(dpi=150)
    img_path = "test_page_20.png"
    pix.save(img_path)
    
    print("Running Surya Layout CLI...")
    # Using the surya_layout CLI directly since internal module paths changed in 0.20.0
    surya_layout_exe = r"C:\Users\Admin\AppData\Roaming\Python\Python311\Scripts\surya_layout.exe"
    result = subprocess.run([surya_layout_exe, img_path], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Successfully generated layout.")
        print(result.stdout)
        print("Surya is working successfully without llama.cpp.")
    else:
        print("Surya layout failed:")
        print(result.stderr)

if __name__ == "__main__":
    main()
