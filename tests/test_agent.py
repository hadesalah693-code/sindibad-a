"""Smoke tests for Sindibad data pipeline."""

import pytest

from app.agent.sindibad_agent import SindibadAgent
from app.data.loader import load_data
from app.services.analyzer import analyze_query


@pytest.fixture(scope="module")
def agent():
    load_data()
    return SindibadAgent()


def test_data_loads():
    store = load_data()
    assert len(store.correlation) > 0
    assert len(store.metric_map) >= 8
    assert store.source.endswith(".xlsx")
    assert "department" in store.correlation.columns


def test_revenue_query(agent):
    result = agent.ask("How is Revenue in Hospitality?")
    assert result.response.grounded
    assert "Revenue" in result.response.executive_summary or "revenue" in result.response.executive_summary.lower()


def test_engagement_department(agent):
    result = agent.ask("Engagement score in IT department")
    assert result.response.grounded
    assert "Engagement" in str(result.metadata.get("metrics_analyzed", []))


def test_guardrail_unknown_metric(agent):
    result = agent.ask("What is the weather in Tokyo?")
    assert not result.response.grounded
    assert "operational database" in result.response.executive_summary


def test_arabic_query(agent):
    result = agent.ask("كيف أداء الإيرادات؟")
    assert result.response.language == "ar"
    assert result.response.grounded


def test_correlation_in_response(agent):
    result = agent.ask("Show Engagement trend in Retail with chart")
    assert result.response.grounded
    assert len(result.charts) >= 1


def test_excel_dashboard_correlation(agent):
    """Correlation r must match pre-computed Excel Dashboard sheet."""
    from app.data.loader import lookup_dashboard_correlation
    from app.services.narrative import build_correlation_context

    store = agent.store
    entry = lookup_dashboard_correlation("Engagement_Score", "Employer_Brand_Score", store)
    assert entry is not None
    assert entry["r"] == pytest.approx(0.769, abs=0.001)

    analysis = analyze_query("ارتباط Employer Brand Score مع Engagement", store)
    ctx = build_correlation_context(analysis, store)
    assert float(str(ctx["r"])) == pytest.approx(0.769, abs=0.001)
    assert ctx["outcome_avg"] == pytest.approx(65.6, abs=0.1)


def test_evidence_and_dashboard_loaded(agent):
    store = agent.store
    assert len(store.evidence_readiness) > 0
    assert len(store.lists) > 0
    assert "Average Employer Brand Score" in store.dashboard["kpis"]
    assert len(store.dashboard["correlations"]) >= 5


def test_workbook_statistics():
    from app.services.dashboard import get_workbook_statistics

    stats = get_workbook_statistics()
    assert len(stats) >= 8
    ids = {s["id"] for s in stats}
    assert "engagement" in ids
    assert "csat" in ids
    assert "strongest_correlation" in ids
