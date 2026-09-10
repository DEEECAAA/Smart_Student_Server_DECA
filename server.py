from flask import Flask, request, jsonify
from celery.result import AsyncResult
from tasks import generate_audio_response_task, generate_text_response_task
from slide_state import set_current_slide, get_current_slide
import os

os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{os.getcwd()}"
os.environ["FLASK_APP"] = "server.py"
app = Flask(__name__)

def generate_response(data, callback):
    if 'audio' not in data:
        return jsonify({"error": "Campo 'audio' mancante nella richiesta"}), 400

    # Fetch the data from the request
    audio_data = data['audio']
    subject = data['subject']
    participation_level = float(data.get('participation_level', 0.5))
    personality = data['personality']
    intelligence = data['intelligence']
    interest = data['interest']
    happiness = data['happiness']

    # Start asynchronous task and return the task ID
    task = callback.delay(audio_data, subject, personality, intelligence, interest, happiness, participation_level)
    return jsonify({"task_id": task.id}), 202

@app.route('/generate_text_response', methods=['POST'])
# Text only response
def generate_text_response():
    # Get the data from the request
    data = request.get_json()

    return generate_response(data, generate_text_response_task)

@app.route('/generate_audio_response', methods=['POST'])
# Text and audio response
def generate_audio_response():
    # Get the data from the request
    data = request.get_json()

    return generate_response(data, generate_audio_response_task)

@app.route('/result/<task_id>', methods=['GET'])
# Get the result of the task
def get_result(task_id):
    result = AsyncResult(task_id, app=generate_text_response_task.app)

    if result.ready():
        # Return the result if the task is completed
        # if the result is a dictionary, return the text and the audio
        # otherwise, return the text, and the audio is empty
        return jsonify({
                "status": "completed", 
                "text": result.result.get("text", result.result), 
                "audio": result.result.get("audio")
            })
    else:
        return jsonify({"status": "pending"})

@app.route('/slide', methods=['POST'])
def slide_update():
    data = request.get_json(force=True) or {}
    set_current_slide(data.get("current_slide", 0))
    return jsonify({"ok": True, "current_slide": get_current_slide()})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)