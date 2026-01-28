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
    
    bg_filters = []
    
    # Logic for modifications to the background stream
    # Note: 'trim' must come first if we are cutting start
    # But -ss is an input option, so it handles the start cut efficiently.
    # However, if we use -ss, timestamps in the filter chain start from 0 relative to the cut point.
    
    audio_filters = ""
    audio_map_opt = "-map 0:a?" # Default fallback

    if intermittent_pause:
        # Generate chained loop filters
        # Frame indices relative to the trimmed input (0s = bg_start_cut)
        current_time = delay_start
        accumulated_frames = 0
        pause_loop_count = int(pause_interval * fps)
        
        loops = []
        
        # Audio concat variables
        concat_inputs = []
        Audio_segments = []
        
        # Initial Audio Segment (0 to delay_start)
        if delay_start > 0:
            Audio_segments.append(f"[0:a]atrim=start=0:end={delay_start},asetpts=PTS-STARTPTS[a_start];")
            concat_inputs.append("[a_start]")
        
        curr_audio_time = delay_start
        
        # Use target_duration here if specified, else effective_duration
        loop_until_time = target_duration if output_duration_minutes > 0 else effective_duration
        
        while current_time < loop_until_time:
            original_frame_idx = int(current_time * fps)
            target_frame_idx = original_frame_idx + accumulated_frames
            
            if current_time >= effective_duration:
                 break

            loops.append(f"loop=loop={pause_loop_count}:size=1:start={target_frame_idx}")
            
            # AUDIO: Add Silence then Audio Segment
            # 1. Silence
            silence_tag = f"[silence_{len(loops)}]"
            Audio_segments.append(f"aevalsrc=0:d={pause_interval}:s=44100{silence_tag};")
            concat_inputs.append(silence_tag)
            
            # 2. Next Audio Segment
            start_t = curr_audio_time
            end_t = start_t + play_interval
            if start_t < effective_duration:
                 seg_tag = f"[a_seg_{len(loops)}]"
                 # Use duration in atrim to be safe? No, start/end is fine with reset PTS
                 # But we must be careful: atrim end is exclusive?
                 Audio_segments.append(f"[0:a]atrim=start={start_t}:end={end_t},asetpts=PTS-STARTPTS{seg_tag};")
                 concat_inputs.append(seg_tag)
            
            accumulated_frames += pause_loop_count
            current_time += play_interval
            curr_audio_time += play_interval
            
            if len(loops) > 1000:
                print("Warning: Too many pause intervals. Truncating.")
                break
        
        if loops:
            bg_filters.append(",".join(loops))
            # Build Audio Filter Chain
            if len(concat_inputs) > 0:
                # Add final segment if any remaining
                # If we broke the loop, we might have remaining audio until end of video?
                # But intermittent pauses usually continue?
                # Let's just concat what we have.
                n_segs = len(concat_inputs)
                Audio_segments.append(f"{''.join(concat_inputs)}concat=n={n_segs}:v=0:a=1[outa];")
                audio_filters = "".join(Audio_segments)
                audio_map_opt = "-map [outa]"

            
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
             
             # Audio: Trim to delay. Let's try without apad first, or explicit whole_dur if we had it.
             # If we remove apad, the audio track is shorter than video. 
             # Some players might dislike it, but FFmpeg should produce valid file.
             # Let's try to use 'atrim' only to see if crash persists.
             audio_filters = f"[0:a]atrim=duration={delay_start}[outa];"
             audio_map_opt = "-map [outa]"
    
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
        f"{audio_filters}"
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
        audio_map_opt,
        
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac", # Re-encode audio
        output_file
    ]
    
    # Fix duration and audio for intermittent pause
    if intermittent_pause:
        new_duration = effective_duration + (accumulated_frames / fps)
        # If output_duration_minutes was set, use that, otherwise use calculated new_duration
        final_t = target_duration if output_duration_minutes > 0 else new_duration
        cmd_ffmpeg.append("-t")
        cmd_ffmpeg.append(str(final_t))
        
        print("Warning: Intermittent video pause processing active.")
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

if __name__ == "__main__":
    # Example usage:
    # Set the background video and delay here
    generate_video(
        background_file="abackground.mp4",
        overlay_file="greenscreen.mp4",
        output_file="final_output.mp4",
        delay_start=4,
        bg_start_cut=3,
        intermittent_pause=False, # Disable intermittent for this test
        freeze_background=True,   # Enable freeze
        output_duration_minutes=33 # 30 seconds output
    )
