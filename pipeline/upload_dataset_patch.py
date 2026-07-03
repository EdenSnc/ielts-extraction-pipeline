import os
import sys

with open(r"C:\Users\Admin\.kaggle\access_token", "r") as f:
    token = f.read().strip()

os.environ['KAGGLE_KEY'] = token
os.environ['KAGGLE_USERNAME'] = 'senoucielamine'

import kagglesdk.kaggle_object
original_from_dict = kagglesdk.kaggle_object.KaggleObject.from_dict.__func__

def patched_from_dict(cls, dikt, **kwargs):
    token = kwargs.pop('token', None) or dikt.pop('token', None)
    obj = original_from_dict(cls, dikt, **kwargs)
    if token is not None:
        obj.token = token
    return obj

kagglesdk.kaggle_object.KaggleObject.from_dict = classmethod(patched_from_dict)

original_to_dict = kagglesdk.kaggle_object.KaggleObject.to_dict

def patched_to_dict(self, *args, **kwargs):
    dikt = original_to_dict(self, *args, **kwargs)
    if hasattr(self, 'token') and self.token is not None:
        dikt['token'] = self.token
    return dikt

kagglesdk.kaggle_object.KaggleObject.to_dict = patched_to_dict

from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

print("Creating dataset...")
try:
    api.dataset_create_new(
        folder=r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\dataset_sample\images',
        dir_mode='zip',
        quiet=False
    )
    print("Dataset upload successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    if hasattr(e, 'response') and e.response is not None:
        print("Response Body:", e.response.text)
    else:
        print("Dataset create error:", repr(e))
