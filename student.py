from enum import Enum
import random
import requests
import re
import os
from datetime import datetime
import json

# ----------------------------
# Config (env-friendly)
# ----------------------------
LLM_URL = os.getenv("LLM_URL", "http://172.21.96.1:11434")

USE_RAG = os.getenv("USE_RAG", "1") == "1"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.65"))  # sotto questo score ignora

MAX_WORDS = int(os.getenv("MAX_WORDS", "60"))

OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.15"))

ROUTER_MODEL = os.getenv("ROUTER_MODEL", "llama3:latest")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3:latest")

# ----------------------------
# Optional RAG
# ----------------------------
try:
    from rag_retriever import retrieve as rag_retrieve
except Exception:
    rag_retrieve = None
    USE_RAG = False

# ----------------------------
# Enums
# ----------------------------
class Personality(Enum):
    SILENT = 1
    SHY = 2
    TALKATIVE = 3
    OUTGOING = 4
    CONFIDENT = 5


class Intelligence(Enum):
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class Interest(Enum):
    UNINTERESTED = 1
    SLIGHTLY_INTERESTED = 2
    NEUTRAL = 3
    INTERESTED = 4
    VERY_INTERESTED = 5


class Happiness(Enum):
    SAD = 1
    UNHAPPY = 2
    NEUTRAL = 3
    HAPPY = 4
    VERY_HAPPY = 5

# ----------------------------
# Helpers
# ----------------------------

def clean_answer(answer: str) -> str:
    # rimuove roba tra [] e tra * *
    cleaned = re.sub(r"\[.*?\]|\*.*?\*", "", answer or "")
    return " ".join(cleaned.split())

def humanize(text: str) -> str:
    t = (text or "").strip()
    # rimuovi incipit tipici da assistant
    t = re.sub(r"^(certo|certamente|okay|ok)[, ]+", "", t, flags=re.I)
    t = re.sub(r"^(come un'intelligenza artificiale|come un'ia|come un'ai |come un modello linguistico)[^\.]*\.\s*", "", t, flags=re.I)
    return t.strip()

def clip_words(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip() + "..."

def needs_clarification(text: str) -> bool:
    t = (text or "").strip().lower()

    # troppo corto
    if len(t) < 12:
        return True

    # poche parole => spesso vago
    if len(t.split()) <= 3:
        return True

    # marker davvero vaghi (non includo "why/how/what is" perché sono domande normali)
    vague_markers = ["spiegare", "dimmi", "puoi", "questo", "quello", "esso", "cosa", "roba"]
    if any(m in t for m in vague_markers) and len(t.split()) < 6:
        return True

    return False

def llm_route(llm_url: str, model: str, transcription: str) -> str:
    """
    Return: 'ANSWER' or 'CLARIFY' (single token)
    """
    system = (
        "Sei un classificatore di routing. Invia ESATTAMENTE un token: RISPONDI o CHIARISCI.\n"
        "CHIARISCI se il discorso del professore è ambiguo/troppo breve/sottospecificato.\n"
        "RISPONDI se puoi rispondere direttamente.\n"
        "Nessun testo aggiuntivo."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": (transcription or "").strip()},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 1.0},
    }
    r = requests.post(f"{llm_url}/api/chat", json=payload, timeout=60)
    r.raise_for_status()
    out = (r.json().get("message", {}).get("content", "")).strip().upper()
    return "CLARIFY" if "CLARIFY" in out else "ANSWER"

def style_hint(personality: Personality, happiness: Happiness, interest: Interest, intelligence: Intelligence) -> str:
    hints = []

    # Personality
    if personality in (Personality.SHY, Personality.SILENT):
        hints.append("Devi essere cauto e cortese; usa frasi brevi.")
    if personality in (Personality.OUTGOING, Personality.TALKATIVE):
        hints.append("Devi essere coinvolgente e vivace; un tocco più espressivo.")
    if personality == Personality.CONFIDENT:
        hints.append("Devi essere diretto e sicuro; minimizza l'essere evasivo.")

    # Happiness
    if happiness in (Happiness.SAD, Happiness.UNHAPPY):
        hints.append("Tono leggermente stanco/piatto, ma rispettoso.")
    if happiness in (Happiness.HAPPY, Happiness.VERY_HAPPY):
        hints.append("Tono positivo e attento.")

    # Interest
    if interest in (Interest.INTERESTED, Interest.VERY_INTERESTED):
        hints.append("Mostra curiosità; se utile, aggiungi un breve dettaglio o un piccolo esempio.")
    if interest in (Interest.UNINTERESTED, Interest.SLIGHTLY_INTERESTED):
        hints.append("Mantienilo al minimo; niente dettagli extra a meno che non siano necessari.")

    # Intelligence (solo sullo stile)
    if intelligence in (Intelligence.VERY_LOW, Intelligence.LOW):
        hints.append("Usa parole più semplici; evita i tecnicismi.")
    if intelligence in (Intelligence.HIGH, Intelligence.VERY_HIGH):
        hints.append("Se opportuno, usa termini precisi, ma sii conciso.")

    return " ".join(hints).strip()


def build_rag_context(transcription: str, current_slide: int) -> str:
    """
    Returns a natural, short notes block (no metadata shown to the model).
    """
    if not (USE_RAG and rag_retrieve is not None):
        return ""

    hits = rag_retrieve(transcription, top_k=RAG_TOP_K, max_slide_index=current_slide) or []
    if not hits:
        return ""

    notes = []
    for h in hits:
        score = float(h.get("score", 0.0))
        if score < RAG_MIN_SCORE:
            continue

        txt = (h.get("text", "") or "").strip()
        if not txt:
            continue

        # tronca per non inondare
        if len(txt) > 500:
            txt = txt[:500].rsplit(" ", 1)[0] + "..."

        notes.append(f"- {txt}")

        # max 2 note per evitare rigidità
        if len(notes) >= 2:
            break

    if not notes:
        return ""

    return "Appunti di lezione pertinenti (da usare come base):\n" + "\n".join(notes) + "\n\n"

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def adapt_enum_from_slider(enum_cls, current_value, slider_value: float, dead_zone: float = 0.10):
    s = clamp01(slider_value)
    current = current_value.value

    lower_bound = 0.5 - dead_zone
    upper_bound = 0.5 + dead_zone

    # zona neutra
    if lower_bound <= s <= upper_bound:
        return current_value

    # verso il basso
    if s < lower_bound:
        strength = (lower_bound - s) / lower_bound

        if s <= 0.15:
            target = 1
        elif s <= 0.30:
            target = random.choice([1, 2])
        else:
            target = random.choice([1, 2, 3])

        new_val = round(current + (target - current) * strength)
        new_val = max(1, min(5, new_val))
        return enum_cls(new_val)

    # verso l'alto
    if s > upper_bound:
        strength = (s - upper_bound) / (1.0 - upper_bound)

        if s >= 0.85:
            target = random.choice([4, 5])
        elif s >= 0.70:
            target = random.choice([3, 4, 5])
        else:
            target = random.choice([2, 3, 4])

        new_val = round(current + (target - current) * strength)
        new_val = max(1, min(5, new_val))
        return enum_cls(new_val)

    return current_value

class Student:
    STARTING_PROMPT = """Sei uno studente intelligente SENEM.

    RUOLO:
    - Sei uno studente universitario che partecipa a una lezione (non il professore).
    - Rispondi solo a parole (niente azioni, niente pensieri, niente indicazioni di scena).
    
    COMPORTAMENTO:
    - Parla in modo naturale come uno studente in classe.
    - Sii breve: 1-3 frasi, massimo {max_words} parole.
    - Non inventare fatti. Se usi gli appunti, attieniti a quelli.
    - Se il discorso del professore non è chiaro, fai UNA breve domanda di chiarimento (e non rispondere).
    - Evita schemi e non sembrare un assistente.
    
    PERSONA (solo tono):
    - Personalità: {personality}
    - Intelligenza: {intelligence}
    - Interesse: {interest}
    - Felicità: {happiness}
    SUGGERIMENTO DI STILE:
    {style_hint}
    
    ARGOMENTO DELLA LEZIONE:
    {subject}
    
    Riporta SOLO le parole dello studente.
    """

    def __init__(self, subject, personality, intelligence, interest, happiness, participation_level=0.5):
        # Assegna i valori passati o genera casualmente
        self.participation_level = clamp01(participation_level)

        base_personality = personality if personality is not None else random.choice(list(Personality))
        base_intelligence = intelligence if intelligence is not None else random.choice(list(Intelligence))
        base_interest = interest if interest is not None else random.choice(list(Interest))
        base_happiness = happiness if happiness is not None else random.choice(list(Happiness))

        self.personality = adapt_enum_from_slider(Personality, base_personality, self.participation_level)
        self.intelligence = adapt_enum_from_slider(Intelligence, base_intelligence, self.participation_level)
        self.interest = adapt_enum_from_slider(Interest, base_interest, self.participation_level)
        self.happiness = adapt_enum_from_slider(Happiness, base_happiness, self.participation_level)

        self.memory = []  # Memoria delle interazioni passate
        self.subject = subject
        self.memory_limit = 5 #possibile cambiare, 5 sembra un buon compromesso
        self.current_slide = 0
        self.starting_prompt = Student.STARTING_PROMPT.format(
            subject=subject,
            personality=self.personality.name,
            intelligence=self.intelligence.name,
            interest=self.interest.name,
            happiness=self.happiness.name,
            style_hint = style_hint(self.personality, self.happiness, self.interest, self.intelligence),
            max_words = MAX_WORDS,
        )

    def generate_response(self, transcription: str) -> str:
        transcription = (transcription or "").strip()

        # 1) RAG context (natural)
        rag_context = build_rag_context(transcription, current_slide= self.current_slide)

        # Aggiungi la memoria alle risposte, includendo le interazioni precedenti
        memory_context = "\n".join([f"Interazione precedente: {memory['transcription']}" for memory in self.memory[-self.memory_limit:]])

        # 2) Routing (cheap heuristic first, then LLM router only if needed)
        if needs_clarification(transcription):
            force_question = True
        else:
            route = llm_route(LLM_URL, ROUTER_MODEL, transcription)
            force_question = (route == "CLARIFY")

        # 3) Compose user message
        professor_prompt = (
            memory_context
            + rag_context
            + "Il professore ha detto:\n"
            + transcription
        )

        messages = [
            {"role": "system", "content": self.starting_prompt},
            {"role": "user", "content": professor_prompt},
        ]

        if force_question:
            messages.append({
                "role": "system",
                "content": "Il discorso del professore è ambiguo/poco specificato. Fai esattamente UNA domanda di chiarimento (una frase). Non rispondere."
            })

        # ---- debug ----
        print("Debug: " + LLM_URL)

        # ---- logging (request) ----
        os.makedirs("logs", exist_ok=True)
        ts = datetime.utcnow().isoformat() + "Z"

        log_entry = {
            "ts": ts,
            "llm_url": LLM_URL,
            "model": CHAT_MODEL,
            "temperature": OLLAMA_TEMPERATURE,
            "subject": self.subject,
            "persona": {
                "personality": self.personality.name,
                "intelligence": self.intelligence.name,
                "interest": self.interest.name,
                "happiness": self.happiness.name,
            },
            "transcription": transcription,
            "request_messages": messages,
            "use_rag": USE_RAG,
            "rag_top_k": RAG_TOP_K,
            "rag_min_score": RAG_MIN_SCORE,
        }

        with open("logs/llm_requests.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # ---- Ollama chat ----
        ollama_payload = {
            "model": CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": OLLAMA_TEMPERATURE,
                "top_p": OLLAMA_TOP_P,
                "repeat_penalty": OLLAMA_REPEAT_PENALTY,
            },
        }

        last_err = None
        response_data = None
        for _ in range(3):
            try:
                response = requests.post(f"{LLM_URL}/api/chat", json=ollama_payload, timeout=180)
                response.raise_for_status()
                response_data = response.json()
                break
            except Exception as e:
                last_err = e

        if response_data is None:
            raise RuntimeError(f"Ollama request failed after retries: {last_err}")

        # ---- logging (response) ----
        with open("logs/llm_responses.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts, "response": response_data}, ensure_ascii=False) + "\n")

        # ---- postprocess ----
        content_message = response_data.get("message", {}).get("content", "")
        content_message = clean_answer(content_message)
        content_message = humanize(content_message)
        content_message = clip_words(content_message, MAX_WORDS)

        # Memorizza l'interazione
        self.memory.append({
            "transcription": transcription,
            "response": content_message,
            "subject": self.subject,
            "timestamp": ts,
        })

        # Mantieni solo le ultime memory_limit interazioni
        if len(self.memory) > self.memory_limit:
            self.memory.pop(0)

        return content_message

    def set_current_slide(self, slide_index: int):
        try:
            self.current_slide = max(0, int(slide_index))
        except Exception:
            self.current_slide = 0