from flask import Flask, request, jsonify, send_file, render_template
import os
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, f"processed_{filename}")
    file.save(input_path)

    # FFmpegコマンドを実行してログを収集
    ffmpeg_log = []
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", input_path, "-vf", "scale=1280:720", output_path],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        ffmpeg_log = result.stderr
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg processing failed: {e}"}), 500

    return jsonify({
        "log": ffmpeg_log,
        "output_file": os.path.basename(output_path)
    })

@app.route('/download/<filename>', methods=['GET'])
def download_video(filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    return send_file(filepath, as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
