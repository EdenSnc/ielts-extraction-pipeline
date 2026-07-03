"""
Poll Kaggle kernel status using the CLI subprocess (avoids API version skew issues)
and download output when done.
"""
import os
import subprocess
import time
import sys

KERNEL = 'senoucielamine/ielts-13-layout-detection'
OUTPUT_DIR = r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_output'

env = os.environ.copy()
env['KAGGLE_KEY'] = open(r'C:\Users\Admin\.kaggle\access_token').read().strip()
env['KAGGLE_USERNAME'] = 'senoucielamine'

KAGGLE_CLI = r'C:\Users\Admin\AppData\Roaming\Python\Python311\Scripts\kaggle.exe'

def get_status():
    result = subprocess.run(
        [KAGGLE_CLI, 'kernels', 'status', KERNEL],
        capture_output=True, text=True, env=env
    )
    return result.stdout.strip() + result.stderr.strip()

def download_output():
    result = subprocess.run(
        [KAGGLE_CLI, 'kernels', 'output', KERNEL, '-p', OUTPUT_DIR],
        capture_output=True, text=True, env=env
    )
    print(result.stdout)
    print(result.stderr)

print(f"Polling {KERNEL}...")
while True:
    status_str = get_status()
    print(f"[{time.strftime('%H:%M:%S')}] {status_str}")
    
    if 'complete' in status_str.lower():
        print("Kernel completed successfully!")
        download_output()
        break
    elif 'error' in status_str.lower() or 'cancel' in status_str.lower():
        print("Kernel failed or was cancelled!")
        download_output()
        break
    elif 'running' in status_str.lower() or 'queued' in status_str.lower():
        time.sleep(15)
    else:
        print(f"Unknown status, waiting: {status_str}")
        time.sleep(15)
