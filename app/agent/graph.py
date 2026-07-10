"""LangGraph workflow orchestrating Sindibad advisory pipeline."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.analyzer import QueryAnalysis, analyze_query
from app.services.charts import charts_for_insights
from app.services.narrative import ExecutiveResponse, build_executive_response


class AgentState(TypedDict):
    query: str
    analysis: QueryAnalysis | None
    response: ExecutiveResponse | None
    charts: list[dict]
    error: str | None


def parse_query_node(state: AgentState) -> dict:
    return {"error": None}


def search_data_node(state: AgentState) -> dict:
    analysis = analyze_query(state["query"])
    return {"analysis": analysis}


def correlate_node(state: AgentState) -> dict:
    # Correlation is embedded in analyze_query / analyze_metric; pass-through.
    return {}


def narrative_node(state: AgentState) -> dict:
    analysis = state.get("analysis")
    if analysis is None:
        return {"error": "Analysis step failed."}
    response = build_executive_response(analysis)
    return {"response": response}


def chart_node(state: AgentState) -> dict:
    analysis = state.get("analysis")
    response = state.get("response")
    if not analysis or not response or not response.grounded:
        return {"charts": []}
    artifacts = charts_for_insights(
        analysis.insights,
        correlation_mode=analysis.correlation_mode,
    )
    return {"charts": [a.figure for a in artifacts]}


def build_sindibad_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse_query", parse_query_node)
    graph.add_node("search_data", search_data_node)
    graph.add_node("correlate", correlate_node)
    graph.add_node("narrative", narrative_node)
    graph.add_node("charts", chart_node)

    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", "search_data")
    graph.add_edge("search_data", "correlate")
    graph.add_edge("correlate", "narrative")
    graph.add_edge("narrative", "charts")
    graph.add_edge("charts", END)

    return graph.compile()
