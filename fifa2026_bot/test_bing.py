from bing_image_downloader import downloader

try:
    downloader.download("Lionel Messi", limit=1,  output_dir='images', adult_filter_off=True, force_replace=False, timeout=60, verbose=True)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
