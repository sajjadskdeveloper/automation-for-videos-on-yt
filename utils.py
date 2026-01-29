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
        # Use Publer API Logic
        # Step 1: Start Job
        print(f"Starting Publer Job for: {url}")
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json;",
            "origin": "https://publer.com",
            "priority": "u=1, i",
            "referer": "https://publer.com/",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        
        payload = {
            "url": url,
            "token": "0.qJOVCkHsrlJ2Cj7xCXCI_9r8VS8PS3n27iw3q-yIT_OARh88krt3iNUk9EUUeGNGZlbNzwdNM53riHKXhV6Vd4A45J17AS2Dy8D9G5n-e0zpVFnwV7krdsWVe-zp9yeTyF-wNWSF-83_ZR8gTEu2hAZdj5cqXqcgL4pLppiSQv31WZtOlNE-Zs_NCO-GRgTdHb9vKMpwDiFWi10o-VB8IIBBJQ5HAk_fBng7XIDPSyL4JnF3uUBi6QKtuZATyMfvCxjLqCVW7NgHEdOU2_EUU876mYOwRMhPQoMXrJtJ256ZtP-8G5tAqNKYS3jOlqGYgxDbKdMuXAlvBfi6pJRIuVB0CluA9vzJh07E28CFrpLnhnCnEU00e6jMY7feclDouDY4zX20U06mwtPxIULV0ctgIujZfms8g-XBQF8iU5ZP39f8-3jKV28fge-dFU5cbxeyyZosAFpmtA8b0Pg5oLPbxn2KlPfKDUzP1My5m0rlscqKznTnadEVO9IQEAe8O78Zh9kNq900AIm26XIPdHbin5yggGqRYW-mnckCJbwyvSkVdhVFxLVD0kVdh9sTroU7m7_8aV9na8CFDocYDHM02U8ynSvza4dlCSinuuIcl8n_2DLj1PLIa-B6jqfKwfjWFM6yjBnzOel_ecUoeCbH1yz_8aS14k8zdDH6-EDB7J8ROJW9yGVQKTrg6nz9X3q7xmLzw_3FEmbozLDxS8VdDsrma1xLLFNiF1DqnLmbZOfLgpLzV9WJ3Gck3t_rgLDjb7zh_X3NL6nYwfltyamfQx5jNr4fmD61bdRVlGqMG9EoA5gpblIeJlikftr9a3mOu9pC9PhOU3gGanJalLMFWLIyLg0sjXh9gmMLNjhHNEa_UqY-KVp5ILGwsF4F-JLBZmTXvMhyOzBeggjt21bm1A_SjCP14Nrg0yfb_pVV_X3Xb1CNnG5MraJfZR2BVd9Vzay771xdRo0cMMayrQ.EtihiRBHWXIncdmWE9TRfQ.d8909f27ba80e16bcb7bd8953162e57216b9148620586119268e37801c0ebe70",
            "macOS": False
        }

        response = requests.post("https://app.publer.com/tools/media", headers=headers, json=payload)
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("job_id")
        
        if not job_id:
            raise Exception("Failed to get job_id from Publer")
            
        print(f"Publer Job ID: {job_id}")
        
        # Step 2: Poll Status
        poll_url = f"https://app.publer.com/api/v1/job_status/{job_id}"
        max_retries = 20
        video_url = None
        
        for i in range(max_retries):
            print(f"Polling status... ({i+1}/{max_retries})")
            status_resp = requests.get(poll_url, headers=headers)
            status_resp.raise_for_status()
            status_data = status_resp.json()
            
            if status_data.get("status") == "complete":
                # Find the video in payload
                payloads = status_data.get("payload", [])
                for item in payloads:
                    if item.get("type") == "video":
                        video_url = item.get("path")
                        break
                break
            elif status_data.get("status") == "failed":
                raise Exception("Publer job failed")
                
            time.sleep(3)
            
        if not video_url:
             raise Exception("Publer job timed out or no video found")
             
        # Step 3: Download via Proxy
        from urllib.parse import quote
        encoded_url = quote(video_url)
        proxy_url = f"https://publer-media-downloader.kalemi-code4806.workers.dev/?url={encoded_url}"
        
        print(f"Downloading from Proxy: {proxy_url[:50]}...")
        file_response = requests.get(proxy_url, stream=True)
        file_response.raise_for_status()
        
        # Determine filename
        filename = f"video_{int(time.time())}.mp4"
        filepath = os.path.join(output_folder, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return filepath

    except Exception as e:
        print(f"Publer download failed: {e}. Trying direct download...")
        return None
