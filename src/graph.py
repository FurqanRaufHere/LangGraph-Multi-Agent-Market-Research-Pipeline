# src/graph.py
from langgraph.graph import StateGraph, START, END
from src.state import init_state, GraphState
from src.agents import ResearcherAgent, AnalystAgent, WriterAgent, ReviewerAgent, NarrativeWriterAgent
from src.fallbacks import CircuitBreaker
from src.observability import log_trace, export_run_summary
from src.pdf_generator import generate_pdf_report
import json
import os

# Initialize agents
researcher = ResearcherAgent()
analyst = AnalystAgent()
writer = WriterAgent()
reviewer = ReviewerAgent()

# Circuit breaker
cb = CircuitBreaker(threshold=3)


# -------------------------------
# Node functions
# -------------------------------
def node_research(state: GraphState) -> GraphState:
    if not cb.ok():
        state["violations"].append("circuit_breaker_open")
        return state
    try:
        state = researcher.run(state)
    except Exception as e:
        state["failure_count"] += 1
        cb.record_failure()
        state["tool_error"] = True
        state["violations"].append("researcher_failed")
    return state


def node_analyst(state: GraphState) -> GraphState:
    try:
        state = analyst.run(state)
    except Exception:
        state["failure_count"] += 1
        state["violations"].append("analyst_failed")
    return state


def node_writer(state: GraphState) -> GraphState:
    try:
        state = writer.run(state)
    except Exception:
        state["failure_count"] += 1
        state["violations"].append("writer_failed")
    return state


def node_reviewer(state: GraphState) -> GraphState:
    try:
        state = reviewer.run(state)
    except Exception:
        state["failure_count"] += 1
        state["violations"].append("reviewer_failed")
    return state


def node_partial_summary(state: GraphState) -> GraphState:
    # graceful short-circuit when too many failures
    state["outputs"]["report_partial"] = {
        "title": f"Partial results for: {state['query']}",
        "summary": "We hit reliability issues; here are partial findings.",
        "facts": state.get("outputs", {}).get("facts", []),
    }
    log_trace("graph.partial_summary", {"failure_count": state["failure_count"]})
    return state


# -------------------------------
# Build the LangGraph
# -------------------------------
Graph = StateGraph(GraphState)  # type: ignore

Graph.add_node("research", node_research)
Graph.add_node("analyst", node_analyst)
Graph.add_node("writer", node_writer)
Graph.add_node("reviewer", node_reviewer)
Graph.add_node("partial", node_partial_summary)

# Edges
Graph.add_edge(START, "research")
Graph.add_edge("research", "analyst")
Graph.add_edge("analyst", "writer")


# Conditional edge: writer → reviewer or partial summary
def writer_to_next(state: GraphState):
    if state.get("failure_count", 0) >= 3:
        return ["partial"]
    return ["reviewer"]


Graph.add_conditional_edges("writer", writer_to_next)

Graph.add_edge("reviewer", END)
Graph.add_edge("partial", END)

# Add Narrative Writer node and edge
narrative_writer = NarrativeWriterAgent()

def node_narrative_writer(state: GraphState) -> GraphState:
    try:
        state = narrative_writer.run(state)
    except Exception:
        state["failure_count"] += 1
        state["violations"].append("narrative_writer_failed")
    return state

Graph.add_node("narrative_writer", node_narrative_writer)
Graph.add_edge("reviewer", "narrative_writer")
Graph.add_edge("narrative_writer", END)

# -------------------------------
# Runner
# -------------------------------
def run(query: str):
    state = init_state(query)
    app = Graph.compile()
    res = app.invoke(state)
    log_trace(
        "graph.run_complete",
        {"query": query, "result_keys": list(res["outputs"].keys()), "violations": res["violations"]},
    )
    export_run_summary(
        {
            "query": query,
            "outputs": res["outputs"],
            "violations": res["violations"],
            "tools_used": res["tools_used"],
        }
    )
    return res


if __name__ == "__main__":
    q = input("Enter your market research query: ")
    result = run(q)
    print(json.dumps(result["outputs"], indent=2, default=str))
    print("Violations:", result["violations"])

    # Display PDF report filename if generated
    if "pdf_report" in result["outputs"]:
        pdf_filename = result["outputs"]["pdf_report"]
        print(f"PDF report generated: {pdf_filename}")
        print(f"Full path: {os.path.abspath(pdf_filename)}")
