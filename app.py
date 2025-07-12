from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import tempfile

app = Flask(__name__)
CORS(app, origins=["https://ramanandmurthy.github.io"])  # limit to GitHub Pages site

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
CLIENT_SECRET = "XYZ-12345-SECURE-TOKEN"

UPLOAD_ENDPOINT = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_ENDPOINT = "https://api.assemblyai.com/v2/transcript"

HEADERS = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    client_token = request.headers.get('X-Client-Token')
    if client_token != CLIENT_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400

    audio = request.files['audio']
    if not audio.filename.endswith('.wav'):
        return jsonify({'error': 'Only .wav files allowed'}), 400

    if len(audio.read()) > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large'}), 413
    audio.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        audio.save(temp.name)

    with open(temp.name, 'rb') as f:
        upload_res = requests.post(UPLOAD_ENDPOINT, headers={"authorization": ASSEMBLYAI_API_KEY}, data=f)
    os.remove(temp.name)

    if upload_res.status_code != 200:
        return jsonify({'error': 'Upload failed'}), 500

    audio_url = upload_res.json()['upload_url']
    config = {
        "audio_url": audio_url,
        "remove_filler_words": True,
        "disfluencies": False,
        "word_boost": [
            "circle back", "synergy", "move the needle", "deep dive", "low-hanging fruit",
            "value add", "alignment", "touch base", "win-win", "leverage", "ideate",
            "pivot", "streamline", "bandwidth", "buy-in", "drill down", "out of the box",
            "take this offline", "mission-critical", "paradigm shift", "pain point",
            "actionable insights", "bleeding edge", "ping me", "level set"
        ],
        "boost_param": "high"
    }

    trans_res = requests.post(TRANSCRIPT_ENDPOINT, headers=HEADERS, json=config)
    if trans_res.status_code != 200:
        return jsonify({'error': 'Transcription init failed'}), 500

    transcript_id = trans_res.json()['id']
    poll_url = f"{TRANSCRIPT_ENDPOINT}/{transcript_id}"

    for _ in range(20):
        res = requests.get(poll_url, headers=HEADERS)
        if res.json().get('status') == 'completed':
            return jsonify({'transcript': res.json()['text']})
        elif res.json().get('status') == 'error':
            return jsonify({'error': 'Transcription failed'}), 500
        import time
        time.sleep(0.5)

    return jsonify({'error': 'Timeout waiting for transcription'}), 504

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)