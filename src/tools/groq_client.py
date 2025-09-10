# src/tools/groq_client.py
import os
import requests
import hashlib
import json
import time
from typing import List, Dict, Any, Optional

ARTIFACT_CACHE = os.environ.get("ARTIFACTS_CACHE", "artifacts")
os.makedirs(ARTIFACT_CACHE, exist_ok=True)
CACHE_FILE = os.path.join(ARTIFACT_CACHE, "groq_cache.json")

def _load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save_cache(c):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)

class GroqClient:
    def __init__(self, api_key: Optional[str]=None, base_url: Optional[str]=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = base_url or os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set in env.")
        self.cache = _load_cache()

    def _cache_key(self, model: str, messages: List[Dict[str, str]]):
        h = hashlib.sha256(json.dumps({"model": model, "messages": messages}, sort_keys=True).encode()).hexdigest()
        return h

    def chat(self, messages: List[Dict[str, str]], model: str, max_tokens: int = 512, temperature: float = 0.2, use_cache: bool = True) -> str:
        key = self._cache_key(model, messages)
        if use_cache and key in self.cache:
            return self.cache[key]["resp"]

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # retries / backoff for 429/5xx
        attempts = 0
        while attempts <= 2:
            attempts += 1
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    text = data["choices"][0]["message"]["content"]
                except Exception:
                    text = json.dumps(data)
                # cache and return
                self.cache[key] = {"resp": text, "meta": {"model": model, "time": time.time()}}
                _save_cache(self.cache)
                return text
            elif resp.status_code in (429, 502, 503, 504):
                # exponential backoff
                wait = 1 * (2 ** (attempts - 1))
                time.sleep(wait)
                continue
            else:
                # non-retriable error
                raise RuntimeError(f"GROQ API error {resp.status_code}: {resp.text}")

        # final fallback
        return "[GROQ_UNAVAILABLE]"
