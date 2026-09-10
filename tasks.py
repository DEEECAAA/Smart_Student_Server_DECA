from celery import Celery
from student import Student, Personality, Intelligence, Interest, Happiness
import whisper
import pyttsx3
import base64
import os
#import torch
#import torchaudio
from slide_state import get_current_slide
#from silero import silero_tts

# Configura Celery per il task broker
app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Global model variable to reduce the loading time each time a task is executed
model = None
model = whisper.load_model("base")
print("Model loaded")

@app.task
def generate_text_response_task(audio_data, subject, personality, intelligence, interest, happiness, participation_level):
    global model

    output_dir = os.path.join(os.path.dirname(__file__), "sounds")
    print("DEBUG: " + output_dir)
    #per evitare problemi di concorrenza
    output_path = os.path.join(output_dir, f"to_transcribe_{os.getpid()}_{os.urandom(4).hex()}.wav")
    print("DEBUG: " + output_path)

    # Check if the folder exists, otherwise create it
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the audio file in base64 format
    with open(output_path, "wb") as audio_file:
        print("DEBUG: Opening file path")
        audio_file.write(base64.b64decode(audio_data))

    #model = whisper.load_model("base")

    # Transcribe the audio
    print("Transcribing...")
    transcription = model.transcribe(output_path, language="it", task="transcribe")["text"]
    print(f"Transcribed test: {transcription}")
    # os.remove(output_path)

    # Create the student object with the given parameters
    personality = Personality(personality)
    intelligence = Intelligence(intelligence)
    interest = Interest(interest)
    happiness = Happiness(happiness)

    student = Student(subject, personality, intelligence, interest, happiness, participation_level)

    # Generate the response text
    current_slide = get_current_slide()
    student.set_current_slide(current_slide)
    response_text = student.generate_response(transcription)

    return response_text

@app.task
def generate_audio_response_task(audio_data, subject, personality, intelligence, interest, happiness, participation_level):
    # Call the text response task and wait for the result

    print(f"Task received with parameters:\n"
          f"audio_data: {len(audio_data) if audio_data else 'None'} bytes\n"
          f"subject: {subject}\n"
          f"personality: {personality}\n"
          f"intelligence: {intelligence}\n"
          f"interest: {interest}\n"
          f"happiness: {happiness}\n"
          f"participation_level: {participation_level}")

    response_task = generate_text_response_task.delay(audio_data, subject, personality, intelligence, interest, happiness, participation_level)
    response_text = response_task.get()

    output_dir = os.path.join(os.path.dirname(__file__), "tmp")

    # Check if the folder exists, otherwise create it
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate the audio file
    # per evitare problemi di concorrenza
    temp_audio_path = os.path.join(output_dir, f"response_{os.getpid()}_{os.urandom(4).hex()}.wav")
    generate_audio(response_text, temp_audio_path)

    with open(temp_audio_path, "rb") as audio_file:
        audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')

    #os.remove(temp_audio_path)

    # Return the response text and the audio file in base64 format
    response = {
        "text": response_text,
        "audio": audio_base64
    }

    return response

# Function to generate audio from text using Silero TTS
#def generate_audio(text, path):
#    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
#    print(f"Using device: {device}")
#    language = 'en'
#    speaker = 'random'
#
#    # Load the model
#    model, example_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
#                                         model='silero_tts',
#                                         language=language,
#                                         speaker='v3_en')
#    # Apply the TTS model
#    audio = model.apply_tts(text=text, speaker=speaker)
#
#    # Save the audio file in 44100 Hz because it's more convenient for Unity
#    torchaudio.save(path, torch.tensor(audio).unsqueeze(0), 44100)

def generate_audio(text, path):
    engine = pyttsx3.init()

    # cerca una voce italiana (Windows SAPI)
    voices = engine.getProperty("voices")
    it_voice_id = None
    for v in voices:
        vinfo = (v.id + " " + str(getattr(v, "name", "")) + " " + str(getattr(v, "languages", ""))).lower()
        if "it" in vinfo or "italian" in vinfo or "italiano" in vinfo:
            it_voice_id = v.id
            break

    if it_voice_id:
        engine.setProperty("voice", it_voice_id)

    engine.setProperty("rate", 170)

    engine.save_to_file(text, path)
    engine.runAndWait()

    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise RuntimeError("TTS failed: output audio file not created or empty.")