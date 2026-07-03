import requests

file_path = r'C:\Users\Admin\Documents\IELTS-PDFS\Cambridge IELTS Academic\13.PDF'
with open(file_path, 'rb') as f:
    response = requests.post('https://file.io/?expires=1d', files={'file': f})

print(response.json())
