"""Plotly chart builders for executive metric visualization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from app.data.loader import get_data_store
from app.services.analyzer import MetricInsight
from app.services.narrative import _display_name, _format_value


@dataclass
class ChartArtifact:
    figure: dict[str, Any]
    title: str
    metric: str


def build_metric_chart(insight: MetricInsight, store=None) -> ChartArtifact | None:
    """Return Plotly figure for a single metric trend."""
    if not insight.chart_series:
        return None

    store = store or get_data_store()
    display = _display_name(insight.metric, store)
    months = insight.chart_series["months"]
    values = insight.chart_series["values"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=values,
            mode="lines+markers",
            name=display,
            line=dict(color="#1a5276", width=3),
            marker=dict(size=8),
            hovertemplate="%{x}<br>%{y}<extra></extra>",
        )
    )
    title = f"{display} — {insight.branch}"
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title=display,
        template="plotly_white",
        height=380,
        margin=dict(l=50, r=30, t=60, b=40),
        font=dict(family="Segoe UI, Arial, sans-serif"),
    )
    return ChartArtifact(
        figure=json.loads(pio.to_json(fig)),
        title=title,
        metric=insight.metric,
    )


def build_correlation_chart(
    primary: MetricInsight,
    secondary_metric: str,
    store=None,
) -> ChartArtifact | None:
    """Dual-axis trend chart for correlated metrics."""
    store = store or get_data_store()
    frame = store.correlation.copy()
    org = store.org_unit_col
    if primary.branch and primary.branch not in ("Network Average", "All Selected"):
        frame = frame[frame[org] == primary.branch]

    if secondary_metric not in frame.columns or primary.metric not in frame.columns:
        return build_metric_chart(primary, store)

    grouped = (
        frame.groupby("month")[[primary.metric, secondary_metric]]
        .mean()
        .sort_index()
    )
    if grouped.empty:
        return None

    p_name = _display_name(primary.metric, store)
    s_name = _display_name(secondary_metric, store)
    months = [m.strftime("%Y-%m") for m in grouped.index]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=grouped[primary.metric].tolist(),
            name=p_name,
            line=dict(color="#1a5276", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=grouped[secondary_metric].tolist(),
            name=s_name,
            yaxis="y2",
            line=dict(color="#c0392b", width=3, dash="dot"),
        )
    )
    title = f"{p_name} ↔ {s_name} — {primary.branch}"
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis=dict(title=p_name, side="left"),
        yaxis2=dict(title=s_name, overlaying="y", side="right"),
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return ChartArtifact(
        figure=json.loads(pio.to_json(fig)),
        title=title,
        metric=primary.metric,
    )


def charts_for_insights(
    insights: list[MetricInsight],
    *,
    correlation_mode: bool = False,
) -> list[ChartArtifact]:
    """Build trend + correlation charts for insights."""
    store = get_data_store()
    artifacts: list[ChartArtifact] = []
    seen_titles: set[str] = set()

    def add(artifact: ChartArtifact | None) -> None:
        if artifact and artifact.title not in seen_titles:
            seen_titles.add(artifact.title)
            artifacts.append(artifact)

    if correlation_mode and len(insights) >= 2:
        add(build_correlation_chart(insights[0], insights[1].metric, store))
        return artifacts

    for insight in insights:
        add(build_metric_chart(insight, store))
        if correlation_mode:
            continue
        for corr in insight.correlated:
            add(build_metric_chart_for_metric(insight.branch, corr["metric"], store))
            add(build_correlation_chart(insight, corr["metric"], store))

    return artifacts


def build_metric_chart_for_metric(
    department: str | None,
    metric: str,
    store=None,
) -> ChartArtifact | None:
    """Build a standalone chart for a correlated metric in the same department."""
    from app.services.analyzer import analyze_metric

    branches = None
    if department and department not in ("Network Average", "All Selected"):
        branches = [department]
    insight = analyze_metric(metric, branches, store)
    if insight:
        return build_metric_chart(insight, store)
    return None


def charts_as_dicts(artifacts: list[ChartArtifact]) -> list[dict[str, Any]]:
    """Backward-compatible list of figure dicts."""
    return [a.figure for a in artifacts]
