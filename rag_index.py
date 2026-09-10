import os
import json
from typing import List, Dict, Tuple

import faiss
from sentence_transformers import SentenceTransformer

EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_DIR = "rag_store"
META_PATH = os.path.join(INDEX_DIR, "meta.jsonl")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")

def read_text_files(root: str) -> List[Tuple[str, str]]:
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith((".txt", ".md")):
                fp = os.path.join(dirpath, fn)
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    out.append((fp, f.read()))
    return out

def read_jsonl_slides(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out

def chunk_text(text: str, chunk_chars: int = 1200, overlap: int = 200) -> List[str]:
    text = " ".join(text.split())
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + chunk_chars)
        chunks.append(text[i:j])
        if j == n:
            break
        i = max(0, j - overlap)
    return chunks

def build_index(knowledge_dir: str = "knowledge") -> None:
    os.makedirs(INDEX_DIR, exist_ok=True)

    model = SentenceTransformer(EMB_MODEL_NAME)

    docs = read_text_files(knowledge_dir)
    slides = read_jsonl_slides("rag_data/slides.jsonl")
    if not docs and not slides:
        raise SystemExit("No knowledge .txt/.md found and no rag_data/slides.jsonl found")

    meta_records: List[Dict] = []
    vectors = []

    for fp, content in docs:
        chunks = chunk_text(content)
        for k, ch in enumerate(chunks):
            meta_records.append({"source": fp, "chunk_id": k, "text": ch})
            vectors.append(ch)

    # ---- Slides (jsonl) ----
    for s in slides:
        text = (s.get("text") or "").strip()
        if not text:
            continue

        sidx = int(s.get("slide_index", -1))
        sname = str(s.get("slide_name", ""))

        chunks = chunk_text(text)
        for k, ch in enumerate(chunks):
            meta_records.append({
                "source": "slides",
                "slide_index": sidx,
                "slide_name": sname,
                "chunk_id": k,
                "text": ch
            })
            vectors.append(ch)

    embeddings = model.encode(vectors, normalize_embeddings=True, show_progress_bar=True)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)  # cosine via normalized embeddings
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)

    with open(META_PATH, "w", encoding="utf-8") as f:
        for r in meta_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Built index with {len(meta_records)} chunks.")
    print(f"Saved: {INDEX_PATH}")
    print(f"Saved: {META_PATH}")

if __name__ == "__main__":
    build_index()
