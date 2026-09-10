import json
from collections import Counter

REQ = "logs/llm_requests.jsonl"
RES = "logs/llm_responses.jsonl"

def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

reqs = list(read_jsonl(REQ))
ress = list(read_jsonl(RES))

# mappa ts -> response
res_by_ts = {r["ts"]: r["response"] for r in ress}

word_counts = []
used_rag = 0
clarify_like = 0
missing = 0
scores = []

for q in reqs:
    ts = q["ts"]
    resp = res_by_ts.get(ts)
    if not resp:
        missing += 1
        continue

    text = (resp.get("message", {}).get("content") or "").strip()
    wc = len(text.split())
    word_counts.append(wc)

    # RAG: controlliamo se nel user content c'era "CONTEXT"
    user_msg = ""
    for m in q.get("request_messages", []):
        if m.get("role") == "user":
            user_msg = m.get("content", "")
            break
    if "CONTEXT (use this as factual grounding):" in user_msg:
        used_rag += 1

    # clarify: euristica semplice
    if text.endswith("?"):
        clarify_like += 1

    # score RAG (se presente nei chunk line)
    if "score=" in user_msg:
        for part in user_msg.split("score=")[1:]:
            try:
                scores.append(float(part[:4]))
            except:
                pass

print("---- REPORT ----")
print("total req:", len(reqs))
print("total res:", len(ress), "missing match:", missing)
print("avg words:", sum(word_counts)/max(1,len(word_counts)))
print("max words:", max(word_counts) if word_counts else 0)
print("rag usage:", used_rag, "/", len(reqs))
print("clarify-like:", clarify_like, "/", len(reqs))
if scores:
    print("avg rag score:", sum(scores)/len(scores))
