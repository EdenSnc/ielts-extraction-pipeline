import os
with open(r"C:\Users\Admin\.kaggle\access_token", "r") as f:
    token = f.read().strip()
os.environ['KAGGLE_KEY'] = token
os.environ['KAGGLE_USERNAME'] = 'senoucielamine'

from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()

import builtins
original_open = builtins.open
def patched_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if 'w' in mode and 'b' not in mode and encoding is None:
        encoding = 'utf-8'
    return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
builtins.open = patched_open

try:
    api.kernels_output("senoucielamine/ielts-13-layout-detection", path=r"C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_output")
    print("Download complete")
except Exception as e:
    print("Download error:", repr(e))
