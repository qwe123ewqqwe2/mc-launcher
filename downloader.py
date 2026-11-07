import requests
import os

BASE_API = "https://bmclapi2.bangbang93.com"

def get_version_list():
    resp = requests.get(f"{BASE_API}/mc/game/version_manifest.json",timeout=15)
    return resp.json()

def download_file(url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    r = requests.get(url, stream=True, timeout=30)
    total_size = int(r.headers.get('content-length', 0))
    with open(save_path,"wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return True
