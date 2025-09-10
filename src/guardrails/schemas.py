# src/guardrails/schemas.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class Fact(BaseModel):
    source: str
    url: Optional[HttpUrl] = None
    excerpt: Optional[str] = None
    content: str

class FinalReport(BaseModel):
    title: str
    summary: str
    key_findings: List[str]
    facts: List[Fact]
    generated_at: datetime