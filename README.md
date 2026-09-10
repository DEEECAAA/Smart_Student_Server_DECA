# SENEM-AI Server

Backend server for **SENEM-AI**, an AI-enhanced virtual classroom designed to support instructor training through the simulation of realistic student behaviour and interactions.

The server coordinates the different components involved in the simulation, including:

* REST API communication with the frontend;
* asynchronous task execution;
* Large Language Model inference;
* student behaviour and response generation;
* Retrieval-Augmented Generation (RAG);
* speech-to-text processing;
* text-to-speech generation;
* classroom slide context management.

> **Platform:** Windows
> **Python:** 3.11.9
> **Project status:** Research prototype

---

## Table of Contents

* [Overview](#overview)
* [System Architecture](#system-architecture)
* [Main Features](#main-features)
* [Technology Stack](#technology-stack)
* [Requirements](#requirements)
* [Windows Installation](#windows-installation)
* [Python Environment Setup](#python-environment-setup)
* [FFmpeg Setup](#ffmpeg-setup)
* [Ollama Setup](#ollama-setup)
* [Redis Setup](#redis-setup)
* [RAG Setup](#rag-setup)
* [Running the Server](#running-the-server)
* [API Endpoints](#api-endpoints)
* [Processing Pipeline](#processing-pipeline)
* [Configuration](#configuration)
* [Troubleshooting](#troubleshooting)
* [Project Structure](#project-structure)
* [Development Notes](#development-notes)

---

# Overview

SENEM-AI provides a virtual classroom environment in which instructors can interact with simulated students.

The backend is responsible for generating and managing the behaviour of these students. Student interactions are produced using a locally hosted Large Language Model and can take into account both the current classroom context and the material currently being presented.

The system supports both text and voice interactions.

For voice interactions, the backend performs the following pipeline:

```text
Teacher Speech
      │
      ▼
   Whisper
Speech-to-Text
      │
      ▼
Student Simulation
      │
      ├───────────────┐
      │               │
      ▼               ▼
    Ollama           RAG
     LLM        Course Material
      │               │
      └───────┬───────┘
              │
              ▼
       Student Response
              │
              ▼
       Text-to-Speech
              │
              ▼
        Audio Response
```

Computationally expensive operations are executed asynchronously using **Celery**, while **Redis** acts as the message broker and result backend.

---

# System Architecture

The server follows a distributed local architecture composed of several services:

```text
+-----------------------+
|       Frontend        |
|   Virtual Classroom   |
+-----------+-----------+
            |
            | HTTP
            ▼
+-----------------------+
|      Flask Server     |
|       server.py       |
+-----------+-----------+
            |
            | Create asynchronous task
            ▼
+-----------------------+
|        Redis          |
| Broker / Result Store |
|    localhost:6379     |
+-----------+-----------+
            |
            ▼
+-----------------------+
|    Celery Worker      |
|       tasks.py        |
+-----------+-----------+
            |
       +----+--------------------+
       |                         |
       ▼                         ▼
+-------------+           +-------------+
|   Whisper   |           |   Ollama    |
| Speech-to-  |           |   Llama 3   |
|    Text     |           |     LLM     |
+-------------+           +------+------+
                                 |
                           +-----+-----+
                           |           |
                           ▼           ▼
                         RAG         Student
                        Context      Behaviour
                           |           |
                           +-----+-----+
                                 |
                                 ▼
                          Text-to-Speech
                                 |
                                 ▼
                         Generated Response
```

The main components are therefore:

1. **Flask** — REST API and communication with the frontend.
2. **Celery** — asynchronous execution of AI and audio-processing tasks.
3. **Redis** — Celery broker, result backend and shared runtime state.
4. **Ollama** — local execution of the Llama 3 language model.
5. **Whisper** — speech-to-text transcription.
6. **FFmpeg** — audio decoding required by Whisper.
7. **pyttsx3** — local text-to-speech generation.
8. **FAISS + SentenceTransformers** — semantic retrieval of relevant course material.

---

# Main Features

### AI Student Simulation

SENEM-AI generates contextual student interactions using a locally hosted Large Language Model.

The simulation is designed to produce student responses that are coherent with the classroom situation and the material available at the current point of the lesson.

---

### Local LLM Execution

LLM inference is performed locally using **Ollama**.

The default model used by the server is:

```text
llama3:latest
```

No external LLM API is required for the standard configuration.

---

### Asynchronous Processing

Potentially expensive operations such as:

* LLM inference;
* speech transcription;
* audio generation;
* student-response generation;

are executed using Celery workers.

This prevents long-running AI operations from blocking Flask HTTP requests.

---

### Speech Recognition

Teacher audio can be processed using **OpenAI Whisper**.

The current configuration uses:

```text
Whisper base
```

The model is loaded by the Celery worker and used to transcribe the instructor's speech.

The transcription pipeline is configured for **Italian speech recognition**.

---

### Text-to-Speech

Generated student responses can be converted into audio using a local text-to-speech pipeline.

The Windows implementation uses:

```text
pyttsx3
```

The server manages generated audio files using unique temporary filenames in order to avoid collisions between concurrently executing Celery tasks.

---

### Retrieval-Augmented Generation

SENEM-AI includes a RAG pipeline that allows student simulations to retrieve information from course slides.

Relevant slide content is retrieved through semantic similarity before the context is provided to the LLM.

The retrieval stack uses:

```text
SentenceTransformers
FAISS
```

The embedding model is:

```text
all-MiniLM-L6-v2
```

By default:

```text
RAG_TOP_K = 3
RAG_MIN_SCORE = 0.65
```

Retrieval is restricted according to the current position in the presentation so that the simulated students do not access material that has not yet been presented.

---

# Technology Stack

| Component               | Technology           |
| ----------------------- | -------------------- |
| Backend API             | Flask                |
| Programming Language    | Python 3.11.9        |
| Task Queue              | Celery               |
| Message Broker          | Redis                |
| Result Backend          | Redis                |
| LLM Runtime             | Ollama               |
| Language Model          | Llama 3              |
| Speech Recognition      | OpenAI Whisper       |
| Audio Processing        | FFmpeg               |
| Text-to-Speech          | pyttsx3              |
| Embeddings              | SentenceTransformers |
| Vector Search           | FAISS                |
| Default Embedding Model | all-MiniLM-L6-v2     |

---

# Requirements

Before installing the project, make sure the following software is available on Windows.

### Required

* **Windows 10 or Windows 11**
* **Python 3.11.9**
* **Git**
* **Ollama**
* **Redis**
* **FFmpeg**

### Recommended

* Microsoft C++ Build Tools

The C++ Build Tools may be required to correctly install packages containing native components, particularly `webrtcvad`.

---

# Windows Installation

Clone the repository:

```powershell
git clone <repository-url>
```

Move into the server directory:

```powershell
cd <server-directory>
```

All commands in this README assume that **PowerShell** is being used.

---

# Python Environment Setup

## 1. Install Python 3.11.9

The project should be executed using:

```text
Python 3.11.9
```

Verify that Python 3.11 is available:

```powershell
py -3.11 --version
```

Expected output:

```text
Python 3.11.9
```

---

## 2. Create the virtual environment

From the project directory:

```powershell
py -3.11 -m venv .venv
```

---

## 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, the PowerShell prompt should contain:

```text
(.venv)
```

---

## 4. Update pip and wheel

```powershell
python -m pip install -U pip wheel
```

---

## 5. Install a compatible setuptools version

The project currently requires:

```powershell
python -m pip install "setuptools<81"
```

This step avoids compatibility problems encountered during dependency installation on Windows.

---

## 6. Install the dependencies

```powershell
pip install -r requirements.txt
```

If `webrtcvad` fails during installation, see the [webrtcvad installation errors](#webrtcvad-installation-errors) section.

---

# FFmpeg Setup

Whisper requires **FFmpeg at runtime**.

Installing the Python package alone is not sufficient: the FFmpeg executable must be available through the Windows `PATH`.

After installing FFmpeg for Windows, add its `bin` directory to the system `PATH`.

For example:

```text
C:\ffmpeg\bin
```

The exact path depends on where FFmpeg was installed.

Close and reopen PowerShell after modifying the `PATH`.

Verify the installation:

```powershell
ffmpeg -version
```

If the command prints the FFmpeg version information, the installation is correctly configured.

Whisper will fail to process audio if FFmpeg cannot be found.

---

# Ollama Setup

SENEM-AI uses **Ollama** to execute its language models locally.

## 1. Install Ollama for Windows

Install the Windows version of Ollama and verify the installation:

```powershell
ollama --version
```

---

## 2. Download the Llama 3 model

The default SENEM-AI configuration expects:

```text
llama3:latest
```

Download it with:

```powershell
ollama pull llama3
```

Verify that it is installed:

```powershell
ollama list
```

The list should contain a Llama 3 model.

---

## 3. Start Ollama

If the Ollama service is not already running:

```powershell
ollama serve
```

The SENEM-AI Windows backend communicates with Ollama locally through:

```text
http://127.0.0.1:11434
```

LLM chat requests are handled through the Ollama chat API.

Keep Ollama running while using SENEM-AI.

---

# Redis Setup

Redis is used as both:

* Celery message broker;
* Celery result backend.

The expected connection is:

```text
redis://localhost:6379/0
```

Before starting SENEM-AI, make sure that the Redis service available on your Windows system is running and listening on:

```text
localhost:6379
```

If `redis-cli` is available, the connection can be checked with:

```powershell
redis-cli ping
```

Expected result:

```text
PONG
```

Celery will not be able to process tasks if Redis is unavailable.

---

# RAG Setup

The RAG system requires a local semantic index built from the course slides.

The index should be created before using slide-aware response generation.

## 1. Build the slide dataset

Run:

```powershell
python tools/build_slides_jsonl.py
```

This generates:

```text
rag_data/slides.jsonl
```

---

## 2. Build the FAISS index

Run:

```powershell
python rag_index.py
```

The indexing process generates the RAG store, including:

```text
rag_store/
├── index.faiss
└── meta.jsonl
```

These files are used during runtime to retrieve the most relevant slide content.

---

## Slide-aware retrieval

SENEM-AI restricts retrieval based on the slide currently being shown.

Conceptually:

```text
retrieved_slide_index <= current_slide_index
```

This is important for student simulation because it prevents simulated students from answering using information that has not yet been presented by the instructor.

---

# Running the Server

SENEM-AI requires several local services to run simultaneously.

A recommended startup order is:

```text
1. Ollama
2. Redis
3. Celery Worker
4. Flask Server
5. Frontend
```

Use separate PowerShell terminals for the different services.

---

## Terminal 1 — Ollama

```powershell
ollama serve
```

If Ollama is already running as a Windows background service, another instance does not need to be started.

---

## Terminal 2 — Redis

Start the Redis instance installed on the Windows machine.

It must be reachable at:

```text
localhost:6379
```

---

## Terminal 3 — Celery Worker

Move to the server directory and activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start Celery with:

```powershell
celery -A tasks worker -l info -P gevent
```

### Important

The `gevent` execution pool is used for Windows compatibility.

Do not start the worker using configurations intended for Unix-based environments.

When the worker starts, Whisper and the other components required by asynchronous tasks are initialized.

Leave this terminal running.

---

## Terminal 4 — Flask Server

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start the backend:

```powershell
python server.py
```

The Flask API is now available to the frontend according to the host and port configured in `server.py`.

---

## Frontend

When both the backend and frontend are running correctly, the SENEM-AI interface is available at:

```text
http://localhost:3000/
```

---

# API Endpoints

The backend exposes the main endpoints required by the SENEM-AI frontend.

## Generate Text Response

```http
POST /generate_text_response
```

Starts the generation of a textual student interaction.

The request is processed asynchronously through Celery.

The endpoint returns a task identifier that can subsequently be used to retrieve the result.

---

## Generate Audio Response

```http
POST /generate_audio_response
```

Handles voice-based interactions.

Depending on the request pipeline, audio can be:

1. processed;
2. transcribed using Whisper;
3. passed to the student simulation;
4. processed by the LLM;
5. converted into a student audio response.

---

## Retrieve Task Result

```http
GET /result/<task_id>
```

Retrieves the status or result of an asynchronous Celery task.

Typical flow:

```text
POST request
     │
     ▼
Celery task created
     │
     ▼
task_id returned
     │
     ▼
GET /result/<task_id>
     │
     ├── task pending
     └── task completed → result
```

---

## Slide Context

```http
POST /slide
```

Updates the classroom slide state used by the backend.

The current slide index is important for RAG retrieval because only information compatible with the current progression of the lesson should be available to the simulated students.

---

# Processing Pipeline

A typical text interaction follows this flow:

```text
Frontend
   │
   ▼
Flask Endpoint
   │
   ▼
Celery Task
   │
   ▼
Student Simulation Logic
   │
   ├── Student State / Behaviour
   │
   ├── Current Slide
   │
   ├── RAG Retrieval
   │
   └── Conversation Context
   │
   ▼
Ollama / Llama 3
   │
   ▼
Generated Student Response
   │
   ▼
Redis Result Backend
   │
   ▼
Frontend
```

For audio interactions:

```text
Teacher Audio
     │
     ▼
Temporary Audio File
     │
     ▼
FFmpeg
     │
     ▼
Whisper
     │
     ▼
Italian Transcription
     │
     ▼
Student Simulation
     │
     ▼
Ollama / Llama 3
     │
     ▼
Generated Text
     │
     ▼
pyttsx3
     │
     ▼
Student Audio Response
```

---

# Configuration

## Language Models

The backend supports configuration of the Ollama models used for different LLM operations.

The default model is:

```text
llama3:latest
```

The relevant configuration includes:

```text
ROUTER_MODEL
CHAT_MODEL
```

Both can use:

```text
llama3:latest
```

---

## RAG Configuration

Default retrieval configuration:

```text
RAG_TOP_K = 3
RAG_MIN_SCORE = 0.65
```

Embedding model:

```text
all-MiniLM-L6-v2
```

---

## Generation Configuration

The enhanced student-response generation pipeline uses the following default generation parameters:

```text
temperature = 0.7
top_p = 0.9
repeat_penalty = 1.15
```

Generated student responses are intentionally kept concise, with a default maximum target of approximately:

```text
60 words
```

This keeps interactions suitable for a classroom conversation rather than producing long assistant-style answers.

---

# Temporary Audio File Management

Audio-processing tasks may run concurrently through Celery.

Using the same temporary filename for multiple requests can therefore lead to:

* files being overwritten;
* transcription of the wrong audio;
* deletion of files still being processed;
* failed TTS operations;
* race conditions between Celery tasks.

The current implementation uses **unique temporary audio filenames** for individual executions.

This isolates concurrent requests and improves the reliability of the speech pipeline.

Temporary resources should be removed once processing is complete.

---

# Troubleshooting

## `requirements.txt` installation fails

Make sure that the project is running with exactly Python 3.11:

```powershell
py -3.11 --version
```

Create a clean environment:

```powershell
py -3.11 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then update the packaging tools:

```powershell
python -m pip install -U pip wheel
```

Install the compatible version of setuptools:

```powershell
python -m pip install "setuptools<81"
```

Finally:

```powershell
pip install -r requirements.txt
```

---

## `webrtcvad` installation errors

Some Windows installations may fail while building `webrtcvad`.

Install the **Microsoft C++ Build Tools**, then reopen PowerShell and reactivate the virtual environment.

Try:

```powershell
pip install webrtcvad
```

Then:

```powershell
pip install -r requirements.txt
```

---

## Whisper cannot find FFmpeg

Typical errors may indicate that an audio file cannot be decoded or that `ffmpeg` cannot be found.

Check:

```powershell
ffmpeg -version
```

If PowerShell reports that the command does not exist, FFmpeg is either:

* not installed;
* or not included in the Windows `PATH`.

Add the FFmpeg `bin` directory to `PATH`, reopen PowerShell and run the command again.

---

## Celery cannot connect to Redis

Make sure Redis is running.

The expected connection is:

```text
redis://localhost:6379/0
```

If available:

```powershell
redis-cli ping
```

Expected:

```text
PONG
```

Then restart the Celery worker.

---

## Celery worker issues on Windows

Use:

```powershell
celery -A tasks worker -l info -P gevent
```

The explicit worker pool is important for the Windows environment.

---

## Ollama connection errors

Check whether Ollama is available:

```powershell
ollama list
```

Verify that Llama 3 is installed.

If not:

```powershell
ollama pull llama3
```

Start Ollama:

```powershell
ollama serve
```

The backend expects the local Ollama service to be reachable at:

```text
127.0.0.1:11434
```

---

## Model not found

If the backend reports that:

```text
llama3:latest
```

cannot be found, run:

```powershell
ollama pull llama3
```

Then verify:

```powershell
ollama list
```

---

## Whisper is slow on first execution

The Whisper model is loaded by the worker.

The initial execution may therefore involve model initialization before transcription starts.

Keep the Celery worker running between interactions instead of restarting it for every request.

---

## RAG files are missing

If the backend cannot find the RAG index, rebuild the dataset:

```powershell
python tools/build_slides_jsonl.py
```

Then rebuild the vector index:

```powershell
python rag_index.py
```

Verify that the following files exist:

```text
rag_data/slides.jsonl
rag_store/index.faiss
rag_store/meta.jsonl
```

---

# Project Structure

The exact repository may evolve during development, but the main server components are organised around the following responsibilities:

```text
SENEM-AI-Server/
│
├── server.py
│   └── Flask application and API endpoints
│
├── tasks.py
│   └── Celery asynchronous tasks
│
├── requirements.txt
│   └── Python dependencies
│
├── rag_index.py
│   └── RAG index generation
│
├── tools/
│   └── build_slides_jsonl.py
│
├── rag_data/
│   └── slides.jsonl
│
├── rag_store/
│   ├── index.faiss
│   └── meta.jsonl
│
└── ...
```

Additional modules handle:

* student behaviour simulation;
* LLM communication;
* prompt construction;
* conversation state;
* speech transcription;
* audio generation;
* temporary file management;
* RAG retrieval.

---

# Development Notes

## Local-first architecture

The SENEM-AI backend is designed to run its main AI components locally.

The standard processing chain therefore uses:

```text
Flask
  ↓
Celery
  ↓
Redis
  ↓
Ollama
  ↓
Llama 3
```

with Whisper and the RAG system integrated where required.

---

## Concurrent execution

AI and audio-processing requests can be computationally expensive.

Celery separates these operations from the main HTTP server and allows the frontend to retrieve completed results asynchronously.

Unique temporary files are used to prevent different audio-processing tasks from interfering with each other.

---

## Classroom-aware generation

SENEM-AI is not intended to behave as a generic chatbot.

Generated interactions are conditioned by the virtual classroom environment, including:

* student simulation logic;
* conversation context;
* teacher interaction;
* current slide;
* retrieved course content.

The RAG system additionally limits access to course information based on lesson progression.

This helps simulated students behave more consistently with what they could reasonably know at that point in the lesson.

---

# Quick Start

Once the project has been installed, the normal Windows startup procedure can be summarised as follows.

### PowerShell 1

```powershell
ollama serve
```

### PowerShell 2

Start the local Redis service.

### PowerShell 3

```powershell
cd <server-directory>
.\.venv\Scripts\Activate.ps1
celery -A tasks worker -l info -P gevent
```

### PowerShell 4

```powershell
cd <server-directory>
.\.venv\Scripts\Activate.ps1
python server.py
```

Then start the SENEM-AI frontend.

The application can then be accessed at:

```text
http://localhost:3000/
```

---

# SENEM-AI

SENEM-AI is a research-oriented system developed to investigate the use of Large Language Models for improving simulated student behaviour in virtual environments for instructor training.

The server integrates local language-model inference, asynchronous processing, speech technologies and retrieval-augmented generation to provide interactive and context-aware simulated classroom experiences.
