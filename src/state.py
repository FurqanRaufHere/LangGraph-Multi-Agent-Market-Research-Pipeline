# src/state.py
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class Fact(BaseModel):
    source: str
    url: Optional[str] = None
    excerpt: Optional[str] = None
    content: str

class FinalReport(BaseModel):
    title: str
    summary: str
    key_findings: List[str]
    facts: List[Fact]
    generated_at: datetime

# Graph state (shared across nodes)
class GraphState(TypedDict):
    query: str
    context: List[str]
    docs: List[Dict[str, str]]        # raw retrieved docs: {path|url, text, title}
    tools_used: List[str]
    violations: List[str]
    outputs: Dict[str, Any]          # nodes put outputs here, e.g., 'report'
    tool_error: bool
    failure_count: int
    needs_disambiguation: bool
    policy_violation: bool
    schema_ok: bool

def init_state(query: str) -> GraphState:
    return {
        "query": query,
        "context": [],
        "docs": [],
        "tools_used": [],
        "violations": [],
        "outputs": {},
        "tool_error": False,
        "failure_count": 0,
        "needs_disambiguation": False,
        "policy_violation": False,
        "schema_ok": False,
    }
