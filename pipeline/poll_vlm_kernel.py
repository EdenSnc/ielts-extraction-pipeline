"""
poll_vlm_kernel.py
Poll the VLM kernel on Kaggle and download output when finished.
"""
import os
import sys
import time
import json
import builtins
import subprocess

# Enforce UTF-8 for prints
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

KAGGLE_SLUG = "senoucielamine/ielts-13-vlm-interpretation"
OUTPUT_DIR = r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_output\vlm_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Patch open to enforce utf-8 when running downloaded files
original_open = builtins.open
def patched_open(*args, **kwargs):
    if 'encoding' not in kwargs and (len(args) < 2 or 'b' not in args[1]):
        kwargs['encoding'] = 'utf-8'
    return original_open(*args, **kwargs)
builtins.open = patched_open

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=False)
    stdout = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
    stderr = res.stderr.decode('utf-8', errors='replace') if res.stderr else ""
    return res.returncode, stdout, stderr

print(f"Polling {KAGGLE_SLUG}...")
while True:
    code, out, err = run_cmd(f"kaggle kernels status {KAGGLE_SLUG}")
    if code != 0:
        print(f"Error checking status: {err}")
        time.sleep(15)
        continue
    
    print(out.strip())
    if "complete" in out.lower() or "error" in out.lower():
        break
    time.sleep(15)

if "complete" in out.lower():
    print("Kernel completed successfully! Downloading output...")
    # Clean output dir first
    for f in os.listdir(OUTPUT_DIR):
        try:
            os.remove(os.path.join(OUTPUT_DIR, f))
        except:
            pass
            
    code, out, err = run_cmd(f"kaggle kernels output {KAGGLE_SLUG} -p \"{OUTPUT_DIR}\"")
    if code == 0:
        print(f"Downloaded output to {OUTPUT_DIR}")
        # Show contents of files in download dir
        for f in os.listdir(OUTPUT_DIR):
            print(f" - {f} ({os.path.getsize(os.path.join(OUTPUT_DIR, f))} bytes)")
    else:
        print(f"Error downloading outputs: {err}")
else:
    print("Kernel finished with errors.")
