# src/tools/retriever.py  (Filesystem MCP)
import os
from typing import List, Dict
import glob
import re

class FileRetriever:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = docs_dir
        os.makedirs(self.docs_dir, exist_ok=True)
        self.index = []  # list of dicts {path, text, title}
        self._build_index()

    def _build_index(self):
        files = glob.glob(os.path.join(self.docs_dir, "*.md")) + glob.glob(os.path.join(self.docs_dir, "*.txt"))
        for p in files:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    t = f.read()
                title = os.path.basename(p)
                self.index.append({"path": p, "text": t, "title": title})
            except Exception:
                continue

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        qwords = re.findall(r"\w+", query.lower())
        scored = []
        for doc in self.index:
            text = doc["text"].lower()
            score = sum(text.count(w) for w in qwords)
            if score > 0:
                scored.append((score, doc))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [d for _, d in scored[:top_k]]
