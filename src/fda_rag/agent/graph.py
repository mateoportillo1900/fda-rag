"""Compile the LangGraph agent graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from fda_rag.agent.nodes import generate_node, retrieve_node
from fda_rag.agent.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Module-level compiled graph — import and call .invoke() on this
agent = build_graph()
