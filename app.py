from flask import Flask, request, jsonify
from flask_cors import CORS
import os, requests, tempfile

app = Flask(__name__)
CORS(app, origins=["https://ramanandmurthy.github.io"])

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
CLIENT_SECRET = "XYZ-12345-SECURE-TOKEN"

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if request.headers.get('X-Client-Token') != CLIENT_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio uploaded'}), 400

    audio = request.files['audio']
    if not audio.filename.endswith('.wav'):
        return jsonify({'error': 'Only .wav files allowed'}), 400
    if len(audio.read()) > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large'}), 413
    audio.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio.save(tmp.name)
    with open(tmp.name, 'rb') as f:
        up = requests.post("https://api.assemblyai.com/v2/upload",
                           headers={"authorization": ASSEMBLYAI_API_KEY}, data=f)
    os.remove(tmp.name)

    if up.status_code != 200:
        return jsonify({'error': 'Upload failed'}), 500

    audio_url = up.json()['upload_url']
    trans = requests.post("https://api.assemblyai.com/v2/transcript",
                          headers={"authorization": ASSEMBLYAI_API_KEY},
                          json={"audio_url": audio_url})
    if trans.status_code != 200:
        return jsonify({'error': 'Transcript start failed'}), 500

    tid = trans.json()['id']
    for _ in range(20):
        r = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}",
                         headers={"authorization": ASSEMBLYAI_API_KEY})
        if r.json().get("status") == "completed":
            return jsonify({'transcript': r.json()['text']})
        if r.json().get("status") == "error":
            return jsonify({'error': 'Transcription failed'}), 500
        import time; time.sleep(0.5)
    return jsonify({'error': 'Timeout'}), 504

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)