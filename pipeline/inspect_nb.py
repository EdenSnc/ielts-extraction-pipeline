import json
nb = json.load(open(r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_pipeline.ipynb'))
for i, c in enumerate(nb['cells']):
    src = ''.join(c['source'])
    ct = c['cell_type']
    print(f'=== Cell {i} ({ct}) ===')
    print(src)
    print()
