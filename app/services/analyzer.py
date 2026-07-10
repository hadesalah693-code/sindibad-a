"""Cross-metric correlation and query analysis services."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.data.loader import DataStore, get_data_store, get_risk_direction

# Bilingual keyword → canonical metric column mapping (Doha Oasis schema)
METRIC_ALIASES: dict[str, str] = {
    "revenue": "Revenue_QAR",
    "الإيرادات": "Revenue_QAR",
    "income": "Revenue_QAR",
    "engagement": "Engagement_Score",
    "مشاركة": "Engagement_Score",
    "المشاركة": "Engagement_Score",
    "انخراط": "Engagement_Score",
    "الانخراط": "Engagement_Score",
    "الانخراط الوظيفي": "Engagement_Score",
    "training": "Training_Completion_Rate",
    "تدريب": "Training_Completion_Rate",
    "التدريب": "Training_Completion_Rate",
    "sla": "SLA_Compliance",
    "compliance": "SLA_Compliance",
    "الالتزام": "SLA_Compliance",
    "turnover": "Turnover_Rate",
    "دوران": "Turnover_Rate",
    "retention": "Turnover_Rate",
    "satisfaction": "Customer_Satisfaction",
    "رضا": "Customer_Satisfaction",
    "absence": "Absence_Rate",
    "vacancy": "Vacancy_Rate",
    "complaint": "Complaint_Rate",
    "brand": "Employer_Brand_Score",
    "employer brand": "Employer_Brand_Score",
    "علامة تجارية": "Employer_Brand_Score",
    "العلامة التجارية": "Employer_Brand_Score",
    "صاحب عمل": "Employer_Brand_Score",
    "roi": "Human_Capital_ROI",
    "productivity": "Revenue_Per_Employee",
    "overtime": "Overtime_Cost_QAR",
    "impact": "Composite_HC_Impact_Score",
    "succession": "Succession_Coverage",
    "risk": "Operational_Risk_Score",
    "headcount": "Average_Headcount",
    "workforce": "Average_Headcount",
    "employees": "Average_Headcount",
}

DEPARTMENT_ALIASES: dict[str, str] = {
    "hospitality": "Hospitality",
    "retail": "Retail",
    "facilities": "Facilities",
    "security": "Security",
    "finance": "Finance",
    "hr": "HR",
    "marketing": "Marketing",
    "it": "IT",
    "operations": "Operations",
    "customer experience": "Customer Experience",
    "cx": "Customer Experience",
    "الضيافة": "Hospitality",
    "التجزئة": "Retail",
}


@dataclass
class MetricInsight:
    metric: str
    latest_value: float
    previous_value: float | None
    trend: str
    trend_pct: float | None
    branch: str | None  # department label (kept for API compatibility)
    month: str
    is_risk: bool
    risk_reason: str | None = None
    correlated: list[dict[str, Any]] = field(default_factory=list)
    chart_series: dict[str, list] | None = None


@dataclass
class QueryAnalysis:
    found: bool
    metrics: list[str]
    branches: list[str]  # departments
    insights: list[MetricInsight]
    unknown_terms: list[str]
    language: str
    wants_chart: bool
    correlation_mode: bool = False


def detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    return "en"


def wants_visualization(text: str) -> bool:
    keywords = (
        "chart", "graph", "plot", "visual", "trend", "show me",
        "رسم", "مخطط", "عرض", "اتجاه",
    )
    lower = text.lower()
    return any(k in lower for k in keywords)


def is_correlation_query(text: str) -> bool:
    lower = text.lower()
    keywords = (
        "ارتباط", "correlat", "relationship", "related", "link", "linked",
        "between", "versus", " vs ", "impact of", "effect of", "تأثير",
        "علاقة", "العلاقة", "ما العلاقة",
    )
    return any(k in lower for k in keywords)


def _org_col(store: DataStore) -> str:
    return store.org_unit_col


def extract_metrics(query: str, store: DataStore | None = None) -> tuple[list[str], list[str]]:
    store = store or get_data_store()
    available = store.all_metric_columns
    map_names = set(store.metric_map["metric_name"].tolist()) if not store.metric_map.empty else set()
    display_names = (
        set(store.metric_map["display_name"].str.lower().tolist())
        if not store.metric_map.empty and "display_name" in store.metric_map.columns
        else set()
    )
    found: list[str] = []
    unknown: list[str] = []
    lower = query.lower()

    for alias, canonical in METRIC_ALIASES.items():
        if alias in lower and canonical not in found:
            if canonical in available or canonical in store.correlation.columns:
                found.append(canonical)

    if not store.metric_map.empty:
        for _, row in store.metric_map.iterrows():
            col = row["metric_name"]
            display = str(row.get("display_name", "")).lower()
            if (display and display in lower) or col.lower().replace("_", " ") in lower:
                if col not in found:
                    found.append(col)

    for col in available:
        if col.lower().replace("_", " ") in lower and col not in found:
            found.append(col)

    if not found:
        for token in re.findall(r"[a-zA-Z_\u0600-\u06FF]+", query):
            if token.lower() not in METRIC_ALIASES and len(token) > 3:
                unknown.append(token)

    return found, unknown


def extract_branches(query: str, store: DataStore | None = None) -> list[str]:
    store = store or get_data_store()
    org = _org_col(store)
    departments = set(store.correlation[org].unique())
    found: list[str] = []
    lower = query.lower()
    for alias, canonical in DEPARTMENT_ALIASES.items():
        if alias in lower and canonical in departments:
            found.append(canonical)
    for dept in departments:
        if str(dept).lower() in lower and dept not in found:
            found.append(str(dept))
    return found


def _source_frame(metric: str, store: DataStore) -> pd.DataFrame:
    for frame in (store.correlation, store.hr, store.finance, store.brand, store.customer_ops):
        if metric in frame.columns:
            return frame
    raise KeyError(metric)


def _compute_trend(series: pd.Series) -> tuple[str, float | None]:
    if len(series) < 2:
        return "stable", None
    prev, curr = float(series.iloc[-2]), float(series.iloc[-1])
    if prev == 0:
        return "stable", None
    pct = ((curr - prev) / abs(prev)) * 100
    if pct > 0.5:
        return "increasing", round(pct, 1)
    if pct < -0.5:
        return "decreasing", round(pct, 1)
    return "stable", round(pct, 1)


def _pearson(a: pd.Series, b: pd.Series) -> float | None:
    aligned = pd.concat([a, b], axis=1).dropna()
    if len(aligned) < 3:
        return None
    return round(float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1])), 2)


def _evaluate_risk(metric: str, value: float, trend: str, store: DataStore) -> tuple[bool, str | None]:
    direction = get_risk_direction(metric)
    if direction == "below" and trend == "decreasing":
        return True, "Adverse trend — metric is declining"
    if direction == "above" and trend == "increasing":
        return True, "Adverse trend — metric is rising"

    # Check metric_map row for contextual insight
    if not store.metric_map.empty:
        row = store.metric_map[store.metric_map["metric_name"] == metric]
        if not row.empty and trend in ("increasing", "decreasing"):
            logic = str(row.iloc[0].get("insight_example", ""))
            if logic and logic != "nan":
                if (direction == "below" and trend == "decreasing") or (
                    direction == "above" and trend == "increasing"
                ):
                    return True, logic[:120]
    return False, None


def _correlated_insights(
    metric: str,
    department: str | None,
    store: DataStore,
) -> list[dict[str, Any]]:
    if store.metric_map.empty:
        return _auto_correlations(metric, department, store)

    row = store.metric_map[store.metric_map["metric_name"] == metric]
    correlated_names: list[str] = []
    if not row.empty:
        correlated_names = [
            c.strip()
            for c in str(row.iloc[0]["correlated_metrics"]).split(",")
            if c.strip()
        ]
    if not correlated_names:
        return _auto_correlations(metric, department, store)

    results: list[dict[str, Any]] = []
    primary = store.correlation.copy()
    org = _org_col(store)
    if department and department not in ("Network Average", "All Selected"):
        primary = primary[primary[org] == department]

    for corr_metric in correlated_names:
        if corr_metric not in primary.columns:
            continue
        grouped = (
            primary.groupby("month")[[metric, corr_metric]]
            .mean()
            .sort_index()
        )
        if grouped.empty:
            continue
        r = _pearson(grouped[metric], grouped[corr_metric])
        latest = float(grouped[corr_metric].iloc[-1])
        trend, _ = _compute_trend(grouped[corr_metric])
        results.append(
            {
                "metric": corr_metric,
                "correlation": r,
                "latest_value": latest,
                "trend": trend,
            }
        )
    return results


def _auto_correlations(
    metric: str,
    department: str | None,
    store: DataStore,
) -> list[dict[str, Any]]:
    """Discover top correlated columns from Correlation_Data when Metric_Map has no row."""
    primary = store.correlation.copy()
    org = _org_col(store)
    if department and department not in ("Network Average", "All Selected"):
        primary = primary[primary[org] == department]
    if metric not in primary.columns:
        return []

    exclude = {org, "month", metric}
    numeric_cols = [
        c for c in primary.select_dtypes(include="number").columns if c not in exclude
    ]
    grouped = primary.groupby("month")[numeric_cols + [metric]].mean().sort_index()
    scores: list[tuple[str, float]] = []
    for col in numeric_cols:
        r = _pearson(grouped[metric], grouped[col])
        if r is not None:
            scores.append((col, abs(r)))
    scores.sort(key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for col, _ in scores[:3]:
        r = _pearson(grouped[metric], grouped[col])
        latest = float(grouped[col].iloc[-1])
        trend, _ = _compute_trend(grouped[col])
        results.append(
            {
                "metric": col,
                "correlation": r,
                "latest_value": latest,
                "trend": trend,
            }
        )
    return results


def analyze_metric(
    metric: str,
    branches: list[str] | None = None,
    store: DataStore | None = None,
) -> MetricInsight | None:
    store = store or get_data_store()
    org = _org_col(store)
    try:
        frame = _source_frame(metric, store)
    except KeyError:
        return None

    subset = frame.copy()
    dept_label: str | None = None
    if branches:
        subset = subset[subset[org].isin(branches)]
        dept_label = branches[0] if len(branches) == 1 else "All Selected"

    if subset.empty:
        return None

    if dept_label is None and len(subset[org].unique()) > 1:
        series = subset.groupby("month")[metric].mean().sort_index()
        dept_label = "Network Average"
    else:
        if dept_label is None:
            dept_label = str(subset[org].iloc[-1])
        series = subset.sort_values("month").groupby("month")[metric].mean().sort_index()

    if series.empty:
        return None

    trend, trend_pct = _compute_trend(series)
    latest = float(series.iloc[-1])
    previous = float(series.iloc[-2]) if len(series) >= 2 else None
    is_risk, risk_reason = _evaluate_risk(metric, latest, trend, store)
    correlated = _correlated_insights(
        metric, None if dept_label == "Network Average" else dept_label, store
    )

    chart_series = {
        "months": [m.strftime("%Y-%m") for m in series.index],
        "values": [round(float(v), 4) for v in series.values],
    }

    return MetricInsight(
        metric=metric,
        latest_value=round(latest, 4),
        previous_value=round(previous, 4) if previous is not None else None,
        trend=trend,
        trend_pct=trend_pct,
        branch=dept_label,
        month=str(series.index[-1].strftime("%Y-%m")),
        is_risk=is_risk,
        risk_reason=risk_reason,
        correlated=correlated,
        chart_series=chart_series,
    )


def analyze_query(query: str, store: DataStore | None = None) -> QueryAnalysis:
    store = store or get_data_store()
    language = detect_language(query)
    metrics, unknown = extract_metrics(query, store)
    branches = extract_branches(query, store)
    correlation_mode = is_correlation_query(query) and len(metrics) >= 2

    insights: list[MetricInsight] = []
    seen_metrics: set[str] = set()

    focus_metrics = metrics[:2] if correlation_mode else metrics
    for metric in focus_metrics:
        insight = analyze_metric(metric, branches or None, store)
        if insight:
            insights.append(insight)
            seen_metrics.add(metric)

    # Expand correlated metrics only for open-ended (non-correlation) queries
    if not correlation_mode:
        for insight in list(insights):
            for corr in insight.correlated[:3]:
                cm = corr["metric"]
                if cm not in seen_metrics:
                    sub = analyze_metric(cm, branches or None, store)
                    if sub:
                        insights.append(sub)
                        seen_metrics.add(cm)

    found = len(insights) > 0
    return QueryAnalysis(
        found=found,
        metrics=metrics,
        branches=branches,
        insights=insights,
        unknown_terms=unknown if not found else [],
        language=language,
        wants_chart=True if found else wants_visualization(query),
        correlation_mode=correlation_mode,
    )
