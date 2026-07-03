import fitz
import sys

def check_page_boundaries(pdf_path):
    print(f"Checking {pdf_path} for page boundary anomalies...")
    doc = fitz.open(pdf_path)
    word_counts = []
    
    for i in range(len(doc)):
        text = doc[i].get_text()
        words = len(text.split())
        word_counts.append(words)
        
    anomalies = []
    
    # 1. Check for duplicated massive word counts (10,000+ words across 3+ consecutive pages)
    dup_count = 1
    for i in range(1, len(word_counts)):
        curr = word_counts[i]
        prev = word_counts[i-1]
        
        if curr > 10000 and abs(curr - prev) < 100:  # near-identical
            dup_count += 1
            if dup_count >= 3 and i not in anomalies:
                anomalies.append(i)
        else:
            dup_count = 1

    # 2. Check for 10x+ jumps that land on suspiciously high numbers (> 1500)
    for i in range(1, len(word_counts)):
        prev = word_counts[i-1]
        curr = word_counts[i]
        
        if prev > 0 and curr > prev * 10 and curr > 1500:
            if i not in anomalies:
                anomalies.append(i)
        elif curr > 0 and prev > curr * 10 and prev > 1500:
            if i not in anomalies:
                anomalies.append(i)

    print(f"Total pages: {len(doc)}")
    print(f"Average words/page: {sum(word_counts)/max(1, len(word_counts)):.1f}")
    if anomalies:
        print(f"FLAG: page_boundary_anomaly_flag = True")
        print(f"Anomalous page transitions found at pages: {anomalies}")
    else:
        print("No page boundary anomalies detected.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_page_boundaries(sys.argv[1])
    else:
        check_page_boundaries(r"C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS Academic\13.PDF")
