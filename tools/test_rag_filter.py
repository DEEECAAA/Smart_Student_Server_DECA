import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from rag_retriever import retrieve

from rag_retriever import retrieve
print(retrieve("pesto", top_k=3, max_slide_index=0))
print(retrieve("pesto", top_k=3, max_slide_index=10))

