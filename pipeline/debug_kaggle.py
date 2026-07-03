import os
import sys
import logging
import http.client as http_client

# 1. Enable HTTP debugging
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# 2. Set credentials
with open(r"C:\Users\Admin\.kaggle\access_token", "r") as f:
    token = f.read().strip()

os.environ['KAGGLE_KEY'] = token
os.environ['KAGGLE_USERNAME'] = 'senoucielamine'

from kaggle.api.kaggle_api_extended import KaggleApi

print("Initializing Kaggle API...")
api = KaggleApi()
api.authenticate()

print("\n" + "="*50)
print("TEST 1: KERNEL PUSH")
print("="*50)
try:
    # Attempting to push the kernel
    api.kernels_push_cli(folder=r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline')
except Exception as e:
    print("\n--- Kernel Push Caught Exception ---")
    print(repr(e))

print("\n" + "="*50)
print("TEST 2: DATASET UPLOAD (HANG REPRODUCTION)")
print("="*50)
import threading
import _thread

def timeout_handler():
    print("\n[TIMEOUT] Dataset upload hanging for more than 30 seconds. Aborting.")
    _thread.interrupt_main()

timer = threading.Timer(30.0, timeout_handler)
timer.start()

try:
    # Attempting to create the dataset
    api.dataset_create_new(
        folder=r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\dataset_sample\images',
        dir_mode='zip',
        quiet=False
    )
except KeyboardInterrupt:
    print("\n--- Dataset Upload HUNG and was aborted by timeout ---")
except Exception as e:
    print("\n--- Dataset Upload Caught Exception ---")
    print(repr(e))
finally:
    timer.cancel()
