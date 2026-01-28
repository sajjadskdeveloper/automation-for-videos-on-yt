import os
import yt_dlp
import requests
from urllib.parse import urlparse

def download_video_from_url(url, output_folder="downloads"):
    """
    Downloads a video from a URL.
    - Uses yt-dlp for supported sites (YouTube, etc.)
    - Falls back to direct download for direct links.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        # Try yt-dlp first
        ydl_opts = {
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename

    except Exception as e:
        print(f"yt-dlp failed: {e}. Trying direct download...")
        
        # Fallback to direct download
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # extract filename from url or header
            a = urlparse(url)
            filename = os.path.basename(a.path)
            if not filename:
                filename = "downloaded_video.mp4"
            
            filepath = os.path.join(output_folder, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
        except Exception as e2:
            print(f"Direct download failed: {e2}")
            return None
