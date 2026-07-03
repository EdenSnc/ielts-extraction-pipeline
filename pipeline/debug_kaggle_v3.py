import os

with open(r"C:\Users\Admin\.kaggle\access_token", "r") as f:
    token = f.read().strip()

os.environ['KAGGLE_KEY'] = token
os.environ['KAGGLE_USERNAME'] = 'senoucielamine'

from kaggle.api.kaggle_api_extended import KaggleApi
from requests.exceptions import HTTPError

api = KaggleApi()
api.authenticate()

print("==== KERNEL PUSH ERROR DETAILS ====")
try:
    api.kernels_push(folder=r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline')
except HTTPError as e:
    print(e)
    if e.response is not None:
        print("RAW STATUS:", e.response.status_code)
        print("RAW BODY:", e.response.text)
except Exception as e:
    print("Other exception:", repr(e))

print("==== DATASET UPLOAD ERROR DETAILS ====")
import _thread
import threading
def timeout_handler():
    print("\n[TIMEOUT] Aborting.")
    _thread.interrupt_main()

timer = threading.Timer(10.0, timeout_handler)
timer.start()

try:
    api.dataset_create_new(
        folder=r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\dataset_sample\images',
        dir_mode='zip',
        quiet=False
    )
except KeyboardInterrupt:
    print("\n--- Timeout hit ---")
except HTTPError as e:
    print(e)
    if e.response is not None:
        print("RAW STATUS:", e.response.status_code)
        print("RAW BODY:", e.response.text)
except Exception as e:
    print("Other exception:", repr(e))
finally:
    timer.cancel()
