from flask import Flask, request, jsonify
import requests
import time
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
UPLOAD_ENDPOINT = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_ENDPOINT = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400

    audio_file = request.files['audio']
    temp_path = "temp_audio.wav"
    audio_file.save(temp_path)

    # Upload to AssemblyAI
    with open(temp_path, 'rb') as f:
        upload_response = requests.post(UPLOAD_ENDPOINT, headers={"authorization": ASSEMBLYAI_API_KEY}, data=f)
    os.remove(temp_path)

    if upload_response.status_code != 200:
        return jsonify({'error': 'Upload failed'}), 500

    audio_url = upload_response.json()['upload_url']

    # Start transcription
    transcript_request = {
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

    transcript_response = requests.post(TRANSCRIPT_ENDPOINT, headers=headers, json=transcript_request)

    if transcript_response.status_code != 200:
        return jsonify({'error': 'Transcription request failed'}), 500

    transcript_id = transcript_response.json()['id']

    # Poll for completion
    polling_url = f"{TRANSCRIPT_ENDPOINT}/{transcript_id}"
    for _ in range(20):
        poll = requests.get(polling_url, headers=headers)
        status = poll.json()['status']
        if status == 'completed':
            return jsonify({'transcript': poll.json()['text']})
        elif status == 'error':
            return jsonify({'error': 'Transcription failed'}), 500
        time.sleep(0.5)

    return jsonify({'error': 'Polling timeout'}), 504

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)