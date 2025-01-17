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
    output_path = os.path.join(OUTPUT_FOLDER, f"processed_{os.path.splitext(filename)[0]}.mp4")
    file.save(input_path)

    # FFmpegコマンドを実行して変換ログを収集
    ffmpeg_log = []
    try:
        # H.264 (avc1) Mainプロファイル変換 + 比率維持で1400x1400以内に収める
        result = subprocess.run(
            [
                "ffmpeg", "-i", input_path,
                "-vf", "scale='min(1400,iw):min(1400,ih)':force_original_aspect_ratio=decrease",
                "-c:v", "libx264", "-profile:v", "main", "-preset", "fast",
                "-movflags", "+faststart",  # シーク対応
                "-c:a", "aac", "-b:a", "128k",  # AAC音声コーデック
                output_path
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        ffmpeg_log = result.stderr
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg processing failed: {e}"}), 500
    finally:
        # 変換元のファイルを削除
        if os.path.exists(input_path):
            os.remove(input_path)

    # ffprobeコマンドを実行して変換後の動画情報を取得
    ffprobe_log = []
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_format", "-show_streams",
                "-print_format", "json",
                output_path
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        ffprobe_log = result.stdout
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFprobe failed: {e}"}), 500

    # 変換ログとffprobe結果を返す
    return jsonify({
        "ffmpeg_log": ffmpeg_log,
        "ffprobe_log": ffprobe_log,
        "output_file": os.path.basename(output_path)
    })

@app.route('/download/<filename>', methods=['GET'])
def download_video(filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    # ファイル送信後に削除
    response = send_file(filepath, as_attachment=True)
    os.remove(filepath)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
