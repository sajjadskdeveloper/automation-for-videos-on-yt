import os

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
        # Try pytubefix
        from pytubefix import YouTube
        
        yt = YouTube(url)
        # Get highest resolution progressive stream if possible, or best video
        stream = yt.streams.get_highest_resolution() 
        if not stream:
             # Fallback to filtering mp4
             stream = yt.streams.filter(file_extension='mp4').first()
             
        if stream:
             filename = stream.download(output_path=output_folder)
             return filename
        else:
             raise Exception("No suitable stream found")

    except Exception as e:
        print(f"pytubefix failed: {e}. Trying direct download...")
        
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
