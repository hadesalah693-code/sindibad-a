"""Sindibad Agent — Virtual Strategic Advisor for Al Khebra Driving School."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent.graph import build_sindibad_graph
from app.data.loader import DataStore, get_data_store, load_data
from app.services.analyzer import QueryAnalysis, analyze_query
from app.services.narrative import ExecutiveResponse, _display_name, _format_value, build_executive_response
from app.services.charts import ChartArtifact, charts_for_insights

GUARDRAIL_MESSAGE_EN = (
    "My current analysis of the operational database does not contain this information."
)
GUARDRAIL_MESSAGE_AR = (
    "تحليلي الحالي لقاعدة البيانات التشغيلية لا يحتوي على هذه المعلومات."
)


@dataclass
class AgentResult:
    query: str
    response: ExecutiveResponse
    analysis: QueryAnalysis | None = None
    charts: list[dict[str, Any]] = field(default_factory=list)
    chart_artifacts: list[ChartArtifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SindibadAgent:
    """
    Executive Strategic AI Advisor.

    Pipeline: query → CSV search → cross-metric correlation → Metric_Map narrative → charts.
    Designed for future Adler ERP API integration via the DataStore abstraction.
    """

    def __init__(self, data_store: DataStore | None = None):
        self._store = data_store
        self._graph = build_sindibad_graph()

    @property
    def store(self) -> DataStore:
        if self._store is None:
            self._store = get_data_store()
        return self._store

    def initialize(self, data_dir=None) -> None:
        """Load CSV datasets at startup."""
        self._store = load_data(data_dir)

    def ask(self, query: str, include_charts: bool = True) -> AgentResult:
        """Process a CEO query and return grounded executive insights."""
        result = self._graph.invoke(
            {
                "query": query.strip(),
                "analysis": None,
                "response": None,
                "charts": [],
                "error": None,
            }
        )

        response: ExecutiveResponse = result["response"]
        analysis: QueryAnalysis | None = result.get("analysis")
        chart_artifacts: list[ChartArtifact] = []
        if include_charts and analysis and response.grounded:
            chart_artifacts = charts_for_insights(
                analysis.insights,
                correlation_mode=analysis.correlation_mode,
            )
        charts = [a.figure for a in chart_artifacts] if include_charts else []

        if not response.grounded:
            lang = analysis.language if analysis else "en"
            response.executive_summary = (
                GUARDRAIL_MESSAGE_AR if lang == "ar" else GUARDRAIL_MESSAGE_EN
            )

        return AgentResult(
            query=query,
            response=response,
            analysis=analysis,
            charts=charts,
            chart_artifacts=chart_artifacts,
            metadata={
                "metrics_analyzed": analysis.metrics if analysis else [],
                "departments": analysis.branches if analysis else [],
                "data_source": self.store.source,
            },
        )

    def format_for_display(self, result: AgentResult) -> str:
        """Render executive markdown for Chainlit / API consumers."""
        r = result.response
        ar = r.language == "ar"
        labels = {
            "summary": "الملخص التنفيذي" if ar else "Executive Summary",
            "findings": "أهم النتائج" if ar else "Key Findings",
            "correlation": "تحليل الارتباط" if ar else "Correlation Analysis",
            "action": "الإجراء الاستراتيجي التالي" if ar else "Next Strategic Action",
            "excel_data": "البيانات من Excel" if ar else "Data from Excel",
            "sources": "المصادر" if ar else "Sources",
        }
        lines = [
            f"## {r.headline}",
            "",
            f"**{labels['summary']}**",
            r.executive_summary,
            "",
        ]

        if r.key_findings:
            lines.append(f"**{labels['findings']}**")
            for f in r.key_findings:
                lines.append(f"- {f}")
            lines.append("")

        if r.correlation_analysis:
            lines.append(f"**{labels['correlation']}**")
            for c in r.correlation_analysis:
                lines.append(f"- {c}")
            lines.append("")

        if r.strategic_actions:
            lines.append(f"**{labels['action']}**")
            for a in r.strategic_actions:
                lines.append(f"> {a}")
            lines.append("")

        if result.analysis and result.analysis.insights:
            lines.append(f"**{labels['excel_data']}**")
            store = self.store
            for insight in result.analysis.insights:
                display = _display_name(insight.metric, store)
                if not insight.chart_series:
                    continue
                lines.append(f"\n*{display} — {insight.branch}*")
                lines.append("| الشهر | القيمة |" if ar else "| Month | Value |")
                lines.append("|-------|--------|")
                for month, val in zip(
                    insight.chart_series["months"],
                    insight.chart_series["values"],
                    strict=False,
                ):
                    lines.append(
                        f"| {month} | {_format_value(insight.metric, float(val))} |"
                    )
            lines.append("")

        if result.chart_artifacts:
            chart_note = (
                f"📊 **{len(result.chart_artifacts)} رسم بياني** مرفق أدناه — "
                "كل رسم يعكس بيانات Excel الفعلية."
                if ar
                else f"📊 **{len(result.chart_artifacts)} chart(s)** attached below — "
                "each reflects actual Excel data."
            )
            lines.append(chart_note)
            lines.append("")

        if r.data_citations:
            lines.append("---")
            lines.append(f"*{labels['sources']}: " + ", ".join(set(r.data_citations)) + "*")

        return "\n".join(lines)

    # Direct methods for API / testing without full graph
    def analyze(self, query: str) -> QueryAnalysis:
        return analyze_query(query, self.store)

    def narrate(self, analysis: QueryAnalysis) -> ExecutiveResponse:
        return build_executive_response(analysis)

    def visualize(self, analysis: QueryAnalysis) -> list[dict]:
        return [a.figure for a in charts_for_insights(analysis.insights)]
