from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
import uuid
import time
from werkzeug.utils import secure_filename
from main import generate_video
from utils import download_video_from_url

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DOWNLOAD_FOLDER'] = 'downloads' # For yt-dlp

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Global lock to ensure single threaded generation
generation_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Check if lock is free
    if generation_lock.locked():
        return jsonify({'error': 'Server is busy processing another video. Please try again later.'}), 429

    input_path = None
    input_type = request.form.get('type')

    try:
        # Handle Input
        if input_type == 'url':
            url = request.form.get('url')
            if not url:
                return jsonify({'error': 'No URL provided'}), 400
            
            input_path = download_video_from_url(url, app.config['DOWNLOAD_FOLDER'])
            if not input_path:
                return jsonify({'error': 'Failed to download video from URL'}), 500
                
        elif input_type == 'upload':
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400
            
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(input_path)
            
        else:
            return jsonify({'error': 'Invalid input type'}), 400

        # Generate unique output filename
        output_filename = f"final_{uuid.uuid4()}.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Hardcoded Overlay Path (as per requirement to use built-in)
        overlay_path = "greenscreen.mp4"
        if not os.path.exists(overlay_path):
             return jsonify({'error': 'Greenscreen file not found on server'}), 500

        # Run Generation with Lock
        with generation_lock:
            # Using default parameters as per previous task state
            # You can expose these params in the form if needed later
            generate_video(
                background_file=input_path,
                overlay_file=overlay_path,
                output_file=output_path,
                delay_start=4,
                bg_start_cut=3,
                intermittent_pause=False, # Defaulting to false for simple use case
                freeze_background=True,
                output_duration_minutes=0.5 # Default short duration for testing, can be changed
            )
            
        if os.path.exists(output_path):
            return jsonify({'filename': output_filename})
        else:
             return jsonify({'error': 'Generation failed, output not found'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup input file if needed? 
        # For now, let's keep them or you can delete input_path here.
        # if input_path and os.path.exists(input_path):
        #    os.remove(input_path)
        pass

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
