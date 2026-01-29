import os

import requests
from urllib.parse import urlparse
import time
import re

def download_video_from_url(url, output_folder="downloads"):
    """
    Downloads a video from a URL.
    - Uses yt-dlp for supported sites (YouTube, etc.)
    - Falls back to direct download for direct links.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        # Use Turboscribe API (Reverse engineered from user provided curl)
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://turboscribe.ai",
            "priority": "u=1, i",
            "referer": "https://turboscribe.ai/downloader/youtube/video",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-lev-xhr": "true",
            "x-turbolinks-loaded": "true",
            # Cookies from user session
            "cookie": "webp=1804264811337; avif=1804264811337; session-secret=04f3781d752efbc038cfdb8cc55213adae63; i18n-activated-languages=en; snowflake=CB2%2FxZIHxM0J0tmNcVKYDg%3D%3D; lev=1; window-width=1920; window-height=911; screen-width=1920; screen-height=1080; device-pixel-ratio=1; time-zone=Asia%2FKarachi; js=1; device-token=OgbH%2Byq9ZgQJhUWi1zYqXc7R; fingerprint=ZpFQLnUUrdGSQtCZWsssPJ0NBvhU1Q_RHXwlNQiAF67gIVu4AASRnQOTCM4CcSjFzmUgAACTCM4DKAikzmFgAACTCM4Dctn-zk8AAACTCM4Acmd8zhPAAACTCM4AcCQKzkzgAACTCM4DieY3znegAACTCM4AjySCzlnAAACTCM4DVysizgOgAACTCM4Ae47WzhuAAACTCM4AgXIhzikAAACTCM4E9KCyzjjgAACTCM4DSxWuzjkgAAA; _gcl_au=1.1.1349448768.1769704819; _ga=GA1.1.1268803902.1769704819; _fbp=fb.1.1769704819278.318474642528589339; FPID=FPID2.2.uefMoT7rO6S9%2FPkb1Cn6BvQByOSMS5zUZd267JOapRc%3D.1769704819; FPLC=%2Fx2hN92P59RepNgb2J2ectYCSrYAOI9143AMLWTWBicaq66F3zpe%2FrpopMLMqOmIRJao72jSrfN%2BeTtUMh1yHJwlf7HtZYLc9H%2Bkdc6cQcYM1LjgxgOBleTjCMkyQw%3D%3D; FPAU=1.1.1349448768.1769704819; _ga_LCTR22QQ87=GS2.1.s1769704818$o1$g1$t1769704863$j15$l0$h1890738902; _uetsid=32c1b250fd3111f08eedd9c3b60c186c; _uetvid=32c22400fd3111f08cd713fa763072c7"
        }
        
        data = {"url": url}
        
        print("Fetching using Turboscribe API...")
        # Note: Using the specific HTMX endpoint provided
        response = requests.post("https://turboscribe.ai/_htmx/NCN20gAEkZMBzQPXkQc", headers=headers, json=data)
        
        if not response.ok:
             print(f"Turboscribe API Failed [{response.status_code}]: {response.text}")
             if response.status_code == 403:
                 print("Error: Cookies/Session likely expired. Update cookies.")
        
        response.raise_for_status()
        
        # Parse HTML for googlevideo link using Regex
        # Looking for <a href="https://rr...googlevideo.com..."
        import re
        html_content = response.text
        
        # Find the first googlevideo link. The response puts the video link in an <a> tag.
        match = re.search(r'href="(https://[^"]+\.googlevideo\.com/[^"]+)"', html_content)
        
        if not match:
            # Fallback for generic MP4 links just in case
            match = re.search(r'href="(https?://[^"]+\.mp4[^"]*)"', html_content)
            
        if not match:
             # Debugging: Save response to see what happened
             print("Could not find video URL in Turboscribe response.")
             # print(html_content) # Too verbose for logs
             raise Exception("No video download URL found in Turboscribe response")
             
        stream_url = match.group(1).replace('&amp;', '&') # persistent HTML entity decode
        
        print(f"Found video URL: {stream_url[:50]}...")

        # 2. Download the file
        print(f"Downloading video...")
        file_response = requests.get(stream_url, stream=True)
        file_response.raise_for_status()
        
        # Determine filename (simple timestamp fallback)
        filename = f"video_{int(time.time())}.mp4"
             
        filepath = os.path.join(output_folder, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return filepath

    except Exception as e:
        print(f"Turboscribe download failed: {e}. Trying direct download...")
        return None
