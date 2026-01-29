import os

import requests
from urllib.parse import urlparse
import time

def download_video_from_url(url, output_folder="downloads"):
    """
    Downloads a video from a URL.
    - Uses yt-dlp for supported sites (YouTube, etc.)
    - Falls back to direct download for direct links.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        from pytubefix import YouTube
        from pytubefix.cli import on_progress

        print(f"Downloading video from: {url}")
        
        # Initialize YouTube object with the URL
        yt = YouTube(url, on_progress_callback=on_progress)
        
        # Get the highest resolution stream
        ys = yt.streams.get_highest_resolution()
        
        if not ys:
            raise Exception("No suitable stream found")

        # Generate a safe filename
        safe_title = "".join([c for c in yt.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title}.mp4"
        
        # Download the video
        print(f"Downloading '{yt.title}'...")
        filepath = ys.download(output_path=output_folder, filename=filename)
        
        print(f"Download complete: {filepath}")
        return filepath

    except Exception as e:
        print(f"Pytubefix download failed: {e}")
        return None
