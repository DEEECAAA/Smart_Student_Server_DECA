import os
import json
from typing import List, Dict

import faiss
from sentence_transformers import SentenceTransformer

EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_DIR = "rag_store"
META_PATH = os.path.join(INDEX_DIR, "meta.jsonl")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")

_model = None
_index = None
_meta = None

def _lazy_load():
    global _model, _index, _meta
    if _model is None:
        _model = SentenceTransformer(EMB_MODEL_NAME)
    if _index is None:
        _index = faiss.read_index(INDEX_PATH)
    if _meta is None:
        _meta = []
        with open(META_PATH, "r", encoding="utf-8") as f:
            for line in f:
                _meta.append(json.loads(line))

def retrieve(query: str, top_k: int = 3, max_slide_index: int | None = None) -> List[Dict]:
    """
    Returns list of dict: meta fields + score
    If max_slide_index is set, exclude slide chunks with slide_index > max_slide_index.
    """
    _lazy_load()

    # chiediamo più risultati per poter filtrare senza restare a corto
    overfetch = max(10, top_k * 10)

    q_emb = _model.encode([query], normalize_embeddings=True)
    scores, idxs = _index.search(q_emb, overfetch)

    results = []
    for score, i in zip(scores[0], idxs[0]):
        if i == -1:
            continue

        m = _meta[i]

        # filtro "no future slides"
        if max_slide_index is not None:
            sidx = m.get("slide_index", None)
            # se non ha slide_index lo consideriamo "sempre valido" (es: appunti generali)
            if sidx is not None and int(sidx) > int(max_slide_index):
                continue

        r = dict(m)
        r["score"] = float(score)
        results.append(r)

        if len(results) >= top_k:
            break

    return results

