import subprocess
import os
import sys
from moviepy.config import FFMPEG_BINARY

def generate_video(background_file, overlay_file, output_file, delay_start=0, freeze_background=False, bg_start_cut=0, intermittent_pause=False, pause_interval=2.0, play_interval=2.0, output_duration_minutes=0):
    """
    Generates a video with a green screen overlay.
    
    Args:
        background_file (str): Path to the background video.
        overlay_file (str): Path to the green screen overlay video.
        output_file (str): Path to save the final video.
        delay_start (int/float): Seconds to wait before showing the overlay.
        freeze_background (bool): If True, freezes the background frame when overlay starts.
        bg_start_cut (int/float): Seconds to cut from the start of the background video.
        intermittent_pause (bool): If True, cycles between playing and pausing the background.
        pause_interval (float): Duration to pause in seconds (used if intermittent_pause=True).
        play_interval (float): Duration to play in seconds (used if intermittent_pause=True).
        output_duration_minutes (float): Total length of output video in minutes. 0 = Original length.
    """
    
    # 1. Locate FFmpeg and FFprobe
    ffmpeg_binary = FFMPEG_BINARY
    
    if os.path.isabs(ffmpeg_binary):
        ffmpeg_dir = os.path.dirname(ffmpeg_binary)
        ffprobe_binary = os.path.join(ffmpeg_dir, "ffprobe.exe")
        if not os.path.exists(ffprobe_binary):
             ffprobe_binary = "ffprobe"
    else:
        ffprobe_binary = "ffprobe"

    print(f"Using FFmpeg: {ffmpeg_binary}")

    # 2. Get Background Duration and FPS
    if not os.path.exists(background_file):
        print(f"Error: Background file '{background_file}' not found.")
        return

    if not os.path.exists(overlay_file):
        print(f"Error: Overlay file '{overlay_file}' not found.")
        return
    
    try:
        # Get duration
        cmd_duration = [
            ffprobe_binary, "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            background_file
        ]
        duration_str = subprocess.check_output(cmd_duration).decode().strip()
        original_bg_duration = float(duration_str)
        
        # Get FPS
        cmd_fps = [
            ffprobe_binary, "-v", "error", 
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            background_file
        ]
        fps_str = subprocess.check_output(cmd_fps).decode().strip()
        # Handle "num/den" format
        if '/' in fps_str:
            num, den = map(float, fps_str.split('/'))
            fps = num / den
        else:
            fps = float(fps_str)
            
        print(f"Original Duration: {original_bg_duration}s, FPS: {fps}")

    except Exception as e:
        print(f"Error probing file: {e}")
        return

    # Adjust duration for start cut
    effective_duration = original_bg_duration - bg_start_cut
    if effective_duration <= 0:
         print(f"Error: Start cut ({bg_start_cut}s) is larger than video duration ({original_bg_duration}s).")
         return
    
    print(f"Effective Duration: {effective_duration}s")
    
    # Determine Target Duration
    target_duration = effective_duration
    if output_duration_minutes > 0:
        target_duration = output_duration_minutes * 60
        print(f"Target Duration Requested: {target_duration}s (original effective: {effective_duration}s)")

    # 3. Construct FFmpeg Command
    
    bg_stream_name = "[0:v]"
    bg_filters = []
    
    # Logic for modifications to the background stream
    # Note: 'trim' must come first if we are cutting start
    # But -ss is an input option, so it handles the start cut efficiently.
    # However, if we use -ss, timestamps in the filter chain start from 0 relative to the cut point.
    
    if intermittent_pause:
        # Generate chained loop filters
        # ... (Intermittent pause logic remains same, but we might check target_duration?)
        # For now, let's assume Intermittent Pause and Output Duration might conflict or need logic.
        # If output_duration > effective, we might need to loop more?
        # The current intermittent implementation loops until `effective_duration`. 
        # If user wants LONGER, we need to loop until `target_duration`.
        
        # Frame indices relative to the trimmed input (0s = bg_start_cut)
        
        current_time = delay_start
        accumulated_frames = 0
        pause_loop_count = int(pause_interval * fps)
        
        # We add loops until we cover the whole duration
        loops = []
        
        # Use target_duration here if specified, else effective_duration
        loop_until_time = target_duration if output_duration_minutes > 0 else effective_duration
        
        while current_time < loop_until_time:
            # We want to pause AT current_time
            # Calculate frame index in the *current* stream state
            # Original frame index would be current_time * fps
            # But previous loops pushed it forward.
            
            # Actually, `loop` filter `start` takes the frame index of the incoming stream.
            # Since we chain them, each filter sees a stream that is longer.
            # But the "content" frame index is what we want to freeze.
            # The content frame `F` is located at `F + accumulated_frames` in the stream?
            # Yes. 
            
            original_frame_idx = int(current_time * fps)
            target_frame_idx = original_frame_idx + accumulated_frames
            
            # If current_time exceeds real video content, we are just looping the last frame?
            # No, 'loop' repeats a frame inside the stream. 
            # If we go past the end of video, we can't loop a frame that doesn't exist.
            # So if target_duration > effective_duration, we must freeze the LAST frame eventually.
            
            if current_time >= effective_duration:
                 # We are past the video end. We need to extend the last frame.
                 # tpad is better for this than loop.
                 break

            loops.append(f"loop=loop={pause_loop_count}:size=1:start={target_frame_idx}")
            
            accumulated_frames += pause_loop_count
            
            # Move time forward: we just paused (time doesn't advance in content), 
            # then we play for play_interval
            current_time += play_interval
            
            # Loop limit check to prevent infinite generation
            if len(loops) > 1000:
                print("Warning: Too many pause intervals. Truncating.")
                break
        
        if loops:
            bg_filters.append(",".join(loops))
        
        # If target duration is longer than what we covered, we might need tpad at the end?
        # Simpler logic for now: Just apply the loops we found.
            
    elif freeze_background:
        # Simple single freeze
        # If output_duration_minutes is set, we freeze until that time.
        
        if output_duration_minutes > 0:
            stop_duration = target_duration - delay_start
        else:
            remaining = effective_duration - delay_start
            stop_duration = remaining + 5 # Buffer
            
        if stop_duration > 0:
             # Stop mode clone extends the stream.
             bg_filters.append(f"trim=duration={delay_start},tpad=stop_mode=clone:stop_duration={stop_duration}")
    
    # Construct the background filter chain
    if bg_filters:
        # Join all background filters
        full_bg_filter = ",".join(bg_filters)
        # Apply to [0:v] and output [bg_processed]
        filter_complex_part1 = f"[0:v]{full_bg_filter}[bg_processed];"
        bg_stream_used = "[bg_processed]"
    else:
        filter_complex_part1 = ""
        bg_stream_used = "[0:v]"

    # Scale overlay, Key, Overlay
    filter_complex = (
        f"{filter_complex_part1}"
        f"[1:v]{bg_stream_used}scale2ref=h=ih*0.85:w=-1[ovr_scaled][bg_ref];"
        f"[ovr_scaled]colorkey=0x00FF00:0.3:0.05[ovr_keyed];"
        f"[bg_ref][ovr_keyed]overlay=(W-w)/2:(H-h)/2:enable='gte(t,{delay_start})'[out]"
    )

    cmd_ffmpeg = [
        ffmpeg_binary, "-y",
        "-hwaccel", "auto",
        "-ss", str(bg_start_cut), 
        "-i", background_file,
        "-stream_loop", "-1", "-i", overlay_file,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        # Note: If we added pauses, the duration is longer!
        # Do we want to cut the video at original effective duration?
        # Or let it be longer (slow motion effect)?
        # usually "Pause" implies extending duration.
        # But if user wants to keep audio sync... audio won't pause with video loop filter!
        # This is a video-only effect. Audio will desync.
        # For this task (green screen automation), maintaining audio sync might not be the goal if audio is disabled or background audio is just music.
        # However, to be safe, I should probably NOT cap duration to original if we want the pauses to be seen.
        # But `main.py` had `-t` before.
        # If we use `-t effective_duration`, we lose the end content that got pushed out.
        # If I remove `-t`, it might go on forever due to loop overlay?
        # `-t` was based on background duration.
        # Let's verify: if intermittent, new duration = effective + accumulated_frames/fps.
        
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "copy", # Audio copy will Desync if we pause video!
        output_file
    ]
    
    # Fix duration and audio for intermittent pause
    if intermittent_pause:
        new_duration = effective_duration + (accumulated_frames / fps)
        # If output_duration_minutes was set, use that, otherwise use calculated new_duration
        final_t = target_duration if output_duration_minutes > 0 else new_duration
        cmd_ffmpeg.append("-t")
        cmd_ffmpeg.append(str(final_t))
        
        print("Warning: Intermittent video pause will desync audio.")
    else:
        # Use target_duration 
        cmd_ffmpeg.append("-t")
        cmd_ffmpeg.append(str(target_duration))

    print("Running FFmpeg command...")
    # print(" ".join(cmd_ffmpeg)) # Command might be too long to print nicely

    try:
        subprocess.run(cmd_ffmpeg, check=True)
        print(f"Done! Output saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with error: {e}")

    print("Running FFmpeg command:")
    print(" ".join(cmd_ffmpeg))

    try:
        subprocess.run(cmd_ffmpeg, check=True)
        print(f"Done! Output saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with error: {e}")

if __name__ == "__main__":
    # Example usage:
    # Set the background video and delay here
    generate_video(
        background_file="background.mp4",
        overlay_file="greenscreen.mp4",
        output_file="final_output.mp4",
        delay_start=4,
        bg_start_cut=3,
        intermittent_pause=False, # Disable intermittent for this test
        freeze_background=True,   # Enable freeze
        output_duration_minutes=33 # 30 seconds output
    )
