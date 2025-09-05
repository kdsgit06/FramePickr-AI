import os
import urllib.request

def download_haarcascade(dest_dir=None):
    if dest_dir is None:
        dest_dir = os.path.join(os.path.dirname(__file__))

    os.makedirs(dest_dir, exist_ok=True)
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    dest_path = os.path.join(dest_dir, "haarcascade_frontalface_default.xml")
    if os.path.exists(dest_path):
        print(f"Already exists: {dest_path}")
        return dest_path
    print("Downloading Haarcascade...")
    urllib.request.urlretrieve(url, dest_path)
    print("Downloaded to:", dest_path)
    return dest_path

if __name__ == "__main__":
    download_haarcascade()
