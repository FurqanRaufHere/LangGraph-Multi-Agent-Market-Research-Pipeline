# src/guardrails/moderation.py
import re
from typing import Tuple

# lightweight heuristic moderation: returns (flagged, reason)
BANNED_PATTERNS = [
    r"\bkill\b", r"\bterror\b", r"\bsexually explicit\b", r"\bchild\b"
]
PROFANITY = [r"\b(fuck|shit|bitch)\b"]

def check_toxicity(text: str) -> Tuple[bool, str]:
    txt = text.lower()
    for p in BANNED_PATTERNS:
        if re.search(p, txt):
            return True, f"policy matched pattern: {p}"
    for p in PROFANITY:
        if re.search(p, txt):
            return True, "contains profanity"
    return False, ""