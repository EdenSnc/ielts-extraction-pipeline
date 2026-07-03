import json
import sys

# Force UTF-8 output
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

log_path = r'C:\Users\Admin\Downloads\ALL ielts resources-new\ocr_pipeline\kaggle_output\ielts-13-layout-detection.log'

with open(log_path, encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.strip().split('\n')
output_lines = []
for line in lines:
    line = line.strip().lstrip(',')
    if not line or line in ['[', ']']:
        continue
    try:
        obj = json.loads(line)
        output_lines.append((obj.get('stream_name', ''), obj.get('time', 0), obj.get('data', '')))
    except:
        pass

# Print everything from after torch install (t > 160s)
print(f"Total output events: {len(output_lines)}")
print("=== From 160s onwards ===")
for stream, t, data in output_lines:
    if t >= 160:
        # Remove ANSI escapes
        import re
        data_clean = re.sub(r'\x1b\[[0-9;]*m', '', data).rstrip()
        print(f"[{t:.1f}s][{stream}] {data_clean}")
