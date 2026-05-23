"""
LangGraph StateGraph for SupportFlow AI agent.

Graph topology:
  START
    └─► classify_intent
          ├─► [answer pre-filled]  ──► generate_answer ──► END
          ├─► [faq / unknown]      ──► retrieve_context ──► generate_answer ──► END
          └─► [tool intents]       ──► run_tool         ──► generate_answer ──► END
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    classify_intent_node,
    generate_answer_node,
    retrieve_context_node,
    route_after_classify,
    run_tool_node,
)
from app.agent.state import AgentState


def _build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("classify", classify_intent_node)
    workflow.add_node("retrieve", retrieve_context_node)
    workflow.add_node("run_tool", run_tool_node)
    workflow.add_node("generate_answer", generate_answer_node)

    # ── Edges ──────────────────────────────────────────────────────────────
    workflow.add_edge(START, "classify")

    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "run_tool": "run_tool",
            "generate_answer": "generate_answer",
        },
    )

    workflow.add_edge("retrieve", "generate_answer")
    workflow.add_edge("run_tool", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow


# ── Compiled graph (module-level singleton, lazy) ──────────────────────────

_compiled = None


def get_graph():
    """Return the compiled graph, building it once on first call."""
    global _compiled
    if _compiled is None:
        _compiled = _build_graph().compile()
    return _compiled


def _make_initial_state(message: str) -> AgentState:
    return {
        "message": message,
        "intent": "",
        "sentiment": "neutral",
        "confidence": 0.0,
        "needs_human": False,
        "retrieved_context": [],
        "sources": [],
        "tool_name": None,
        "tool_input": None,
        "tool_result": None,
        "ticket": None,
        "answer": "",
        "error": None,
    }


def run_agent(message: str) -> AgentState:
    """Synchronous entry point. Runs the full agent graph and returns final state."""
    graph = get_graph()
    return graph.invoke(_make_initial_state(message))
