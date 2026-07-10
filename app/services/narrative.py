"""Executive narrative generation from Metric_Map templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.loader import (
    get_dashboard_kpi,
    get_data_store,
    lookup_dashboard_correlation,
)
from app.services.analyzer import MetricInsight, QueryAnalysis


@dataclass
class ExecutiveResponse:
    headline: str
    executive_summary: str
    key_findings: list[str]
    correlation_analysis: list[str]
    strategic_actions: list[str]
    data_citations: list[str]
    chart_metrics: list[str]
    language: str
    grounded: bool


def _display_name(metric: str, store) -> str:
    if store.metric_map.empty:
        return metric.replace("_", " ")
    row = store.metric_map[store.metric_map["metric_name"] == metric]
    if not row.empty:
        return str(row.iloc[0].get("display_name", metric))
    return metric.replace("_", " ")


def _format_value(metric: str, value: float) -> str:
    if metric in {"Revenue_QAR", "Workforce_Cost_QAR", "Overtime_Cost_QAR", "Turnover_Cost_QAR"}:
        return f"{value:,.0f} QAR"
    if metric in {"Revenue_Per_Employee"}:
        return f"{value:,.0f} QAR/employee"
    if metric in {
        "Engagement_Score",
        "Employer_Brand_Score",
        "Customer_Satisfaction",
        "Composite_HC_Impact_Score",
        "Operational_Risk_Score",
    }:
        return f"{value:.1f}"
    if metric.endswith("_Rate") or metric in {
        "SLA_Compliance",
        "Training_Completion_Rate",
        "Human_Capital_ROI",
        "Offer_Acceptance_Rate",
        "Policy_Acknowledgement_Rate",
        "Mandatory_Training_Completion",
        "Succession_Coverage",
        "Workforce_Cost_Ratio",
    }:
        if abs(value) <= 1.0:
            return f"{value * 100:.1f}%"
        return f"{value:.1f}%"
    return f"{value:,.2f}"


def _trend_label(trend: str, language: str) -> str:
    labels = {
        "en": {"increasing": "increasing", "decreasing": "decreasing", "stable": "stable"},
        "ar": {"increasing": "في ارتفاع", "decreasing": "في انخفاض", "stable": "مستقر"},
    }
    return labels.get(language, labels["en"]).get(trend, trend)


def _build_correlation_narrative(insight: MetricInsight, language: str, store) -> str:
    if not insight.correlated:
        return ""

    mm = store.metric_map[store.metric_map["metric_name"] == insight.metric]
    logic = ""
    if not mm.empty:
        logic = str(mm.iloc[0].get("correlation_logic", ""))

    parts: list[str] = []
    if logic and logic != "nan":
        parts.append(logic)

    for c in insight.correlated[:3]:
        r = c.get("correlation")
        if r is None:
            continue
        strength = "strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak"
        name = _display_name(c["metric"], store)
        if language == "ar":
            parts.append(
                f"{name}: ارتباط {strength} (r={r})، القيمة {_format_value(c['metric'], c['latest_value'])}"
            )
        else:
            parts.append(
                f"{name}: {strength} correlation (r={r}), current {_format_value(c['metric'], c['latest_value'])}"
            )
    return "; ".join(parts)


def _correlation_strength(r: float | None, language: str) -> str:
    if r is None:
        return "غير محسوب" if language == "ar" else "not computed"
    abs_r = abs(r)
    if abs_r >= 0.75:
        return "قوي جداً" if language == "ar" else "very strong"
    if abs_r >= 0.7:
        return "قوي" if language == "ar" else "strong"
    if abs_r >= 0.4:
        return "متوسط" if language == "ar" else "moderate"
    return "ضعيف" if language == "ar" else "weak"


def _pearson_between(store, metric_a: str, metric_b: str, branch: str | None) -> float | None:
    frame = store.correlation.copy()
    org = store.org_unit_col
    if branch and branch not in ("Network Average", "All Selected"):
        frame = frame[frame[org] == branch]
    if metric_a not in frame.columns or metric_b not in frame.columns:
        return None
    grouped = frame.groupby("month")[[metric_a, metric_b]].mean().sort_index()
    if len(grouped) < 3:
        return None
    return round(float(grouped[metric_a].corr(grouped[metric_b])), 3)


def _friendly_metric_name(metric: str, language: str, store=None) -> str:
    """Executive-friendly metric labels (Arabic-first)."""
    if language == "ar":
        labels = {
            "Engagement_Score": "الانخراط الوظيفي",
            "Employer_Brand_Score": "العلامة التجارية كصاحب عمل",
            "Customer_Satisfaction": "رضا العملاء",
            "Training_Completion_Rate": "إكمال التدريب",
        }
        if metric in labels:
            return labels[metric]
    store = store or get_data_store()
    return _display_name(metric, store)


_DASHBOARD_KPI_BY_METRIC: dict[str, str] = {
    "Engagement_Score": "Average Engagement Score",
    "Employer_Brand_Score": "Average Employer Brand Score",
    "Customer_Satisfaction": "Average Customer Satisfaction",
    "Training_Completion_Rate": "Average Training Completion",
}


def _strongest_dashboard_r(store) -> float:
    corrs = store.dashboard.get("correlations", [])
    if not corrs:
        return 0.0
    return max(abs(float(entry["r"])) for entry in corrs)


def _is_strongest_correlation(r: float | None, store) -> bool:
    if r is None:
        return False
    return abs(r) >= _strongest_dashboard_r(store) - 0.001


def _infer_driver_outcome(
    a: MetricInsight, b: MetricInsight
) -> tuple[MetricInsight, MetricInsight]:
    """Pick a plausible driver/outcome pair for narrative (not statistical causality)."""
    driver_priority = ("engagement", "training", "turnover", "absence", "vacancy")
    for token in driver_priority:
        for ins in (a, b):
            if token in ins.metric.lower():
                return ins, b if ins is a else a
    return a, b


def _dashboard_avg_for_metric(metric: str, store) -> float | None:
    label = _DASHBOARD_KPI_BY_METRIC.get(metric)
    if label:
        return get_dashboard_kpi(label, store)
    if metric in store.correlation.columns:
        return float(store.correlation[metric].mean())
    return None


def _format_correlation_avg(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    if metric.endswith("_Rate") and abs(value) <= 1.0:
        return f"{value * 100:.1f}%"
    if metric in {
        "Engagement_Score",
        "Employer_Brand_Score",
        "Customer_Satisfaction",
        "Composite_HC_Impact_Score",
    }:
        return f"{value:.1f}/100"
    return _format_value(metric, value)


def _correlation_pair_key(metric_a: str, metric_b: str) -> frozenset[str]:
    return frozenset({metric_a, metric_b})


def _build_correlation_narrative_ar(
    *,
    pair: frozenset[str],
    driver_name: str,
    outcome_name: str,
    r: float,
    strength: str,
    is_strongest: bool,
    outcome_avg: float | None,
    outcome_metric: str,
    projected: float,
) -> tuple[str, str, list[dict]]:
    outcome_display = _format_correlation_avg(outcome_metric, outcome_avg)
    pair_sub = f"{driver_name} → {outcome_name}"

    if pair == frozenset({"Engagement_Score", "Employer_Brand_Score"}):
        headline = (
            "الانخراط الوظيفي والعلامة التجارية كصاحب عمل يشكّلان "
            "**أقوى ارتباط إيجابي** في لوحة القياس."
            if is_strongest
            else f"الانخراط الوظيفي والعلامة التجارية كصاحب عمل مرتبطان بارتباط **{strength}**."
        )
        summary = (
            f"{headline}<br/><br/>"
            f"**r = {r:.3f}** — ارتباط {strength}: الإدارات ذات الانخراط المرتفع "
            f"تسجل باستمرار درجات علامة تجارية أعلى.<br/><br/>"
            f"**متوسط درجة العلامة التجارية الحالية: {outcome_display}**"
        )
        rec = (
            "الاستثمار في برامج الانخراط يحقق **قيمة مزدوجة**: يقلل مخاطر المغادرة "
            "ويعزز العلامة التجارية دون إنفاق إضافي على التسويق.<br/>"
            f"يُقدّر أن رفع الانخراط بـ 10 نقاط يرفع درجة العلامة التجارية بنحو **{projected} نقطة**."
        )
        metrics = [
            {"label": "قوة الارتباط", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent", "icon": "↔"},
            {"label": "متوسط العلامة التجارية", "value": outcome_display, "sub": "عبر جميع الإدارات", "theme": "warning", "icon": "◎"},
            {"label": "المحرك الرئيسي", "value": "الانخراط", "sub": "أعلى رافعة تأثير", "theme": "success", "icon": "▲"},
            {"label": "الأثر", "value": "عائد مزدوج", "sub": "احتفاظ + جذب", "theme": "success", "icon": "✦"},
        ]
        return summary, rec, metrics

    if pair == frozenset({"Training_Completion_Rate", "Customer_Satisfaction"}):
        summary = (
            f"ارتباط **{strength}** بين {driver_name} و{outcome_name} "
            f"(**r = {r:.3f}**).<br/><br/>"
            f"الإدارات التي تحقق معدلات إكمال تدريب أعلى تميل إلى تسجيل درجات رضا عملاء أفضل — "
            f"لكن هذا **ليس أقوى الارتباطات** في شبكة القياس (الأقوى: الانخراط ↔ العلامة التجارية).<br/><br/>"
            f"**متوسط رضا العملاء الحالي: {outcome_display}**"
        )
        rec = (
            "رفع معدلات إكمال التدريب — خاصة التدريب الإلزامي — يرتبط بتحسّن تجربة العملاء "
            "على مستوى الإدارات.<br/>"
            f"يُقدّر أن رفع إكمال التدريب بـ 10 نقاط مئوية يرتبط بتحسّن رضا العملاء "
            f"بنحو **{projected} نقطة**."
        )
        metrics = [
            {"label": "قوة الارتباط", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent", "icon": "↔"},
            {"label": "متوسط رضا العملاء", "value": outcome_display, "sub": "عبر جميع الإدارات", "theme": "warning", "icon": "◎"},
            {"label": "المحرك", "value": "إكمال التدريب", "sub": "رافعة تشغيلية", "theme": "success", "icon": "▲"},
            {"label": "الأثر", "value": "جودة الخدمة", "sub": "تدريب → تجربة العميل", "theme": "success", "icon": "✦"},
        ]
        return summary, rec, metrics

    direction = "إيجابي" if r >= 0 else "سلبي"
    strongest_note = (
        " — **أقوى ارتباط في لوحة القياس**."
        if is_strongest
        else "."
    )
    summary = (
        f"تحليل الارتباط بين {driver_name} و{outcome_name} يُظهر علاقة **{strength}** "
        f"({direction}){strongest_note}<br/><br/>"
        f"**r = {r:.3f}**: عند ارتفاع {driver_name} تميل {outcome_name} إلى "
        f"{'التحسّن' if r >= 0 else 'التراجع'} على مستوى الإدارات.<br/><br/>"
        f"**متوسط {outcome_name} الحالي: {outcome_display}**"
    )
    rec = (
        f"التركيز على تحسين {driver_name} قد ينعكس إيجاباً على {outcome_name}.<br/>"
        f"يُقدّر أن تحسّن {driver_name} بمقدار 10 نقاط يرتبط بتغيّر في {outcome_name} "
        f"بنحو **{projected} نقطة**."
    )
    metrics = [
        {"label": "قوة الارتباط", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent", "icon": "↔"},
        {"label": f"متوسط {outcome_name}", "value": outcome_display, "sub": "عبر جميع الإدارات", "theme": "warning", "icon": "◎"},
        {"label": "المحرك", "value": driver_name.split()[0], "sub": "رافعة محتملة", "theme": "success", "icon": "▲"},
        {"label": "الأثر", "value": "مرتبط", "sub": f"{driver_name} → {outcome_name}", "theme": "success", "icon": "✦"},
    ]
    return summary, rec, metrics


def _build_correlation_narrative_en(
    *,
    pair: frozenset[str],
    driver_name: str,
    outcome_name: str,
    r: float,
    strength: str,
    is_strongest: bool,
    outcome_avg: float | None,
    outcome_metric: str,
    projected: float,
) -> tuple[str, str, list[dict]]:
    outcome_display = _format_correlation_avg(outcome_metric, outcome_avg)
    pair_sub = f"{driver_name} → {outcome_name}"

    if pair == frozenset({"Engagement_Score", "Employer_Brand_Score"}):
        headline = (
            "Employee engagement and employer brand form the **strongest positive link** "
            "on the executive dashboard."
            if is_strongest
            else f"Employee engagement and employer brand show a **{strength}** relationship."
        )
        summary = (
            f"{headline}<br/><br/>"
            f"**r = {r:.3f}** — {strength} correlation: departments with higher engagement "
            f"consistently score higher on employer brand.<br/><br/>"
            f"**Current average employer brand score: {outcome_display}**"
        )
        rec = (
            "Investing in engagement programs delivers **dual ROI** — reducing turnover risk "
            "while strengthening employer brand without extra marketing spend.<br/>"
            f"Raising engagement by 10 points is estimated to lift employer brand by ~**{projected} points**."
        )
        metrics = [
            {"label": "Correlation Strength", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent"},
            {"label": "Average Employer Brand", "value": outcome_display, "sub": "across all departments", "theme": "warning"},
            {"label": "Main Driver", "value": "Engagement", "sub": "highest-leverage lever", "theme": "success"},
            {"label": "Impact", "value": "Dual ROI", "sub": "retention + attraction", "theme": "success"},
        ]
        return summary, rec, metrics

    if pair == frozenset({"Training_Completion_Rate", "Customer_Satisfaction"}):
        summary = (
            f"A **{strength}** link between {driver_name} and {outcome_name} "
            f"(**r = {r:.3f}**).<br/><br/>"
            f"Departments with higher training completion tend to report better customer satisfaction — "
            f"but this is **not the strongest relationship** on the dashboard "
            f"(strongest: engagement ↔ employer brand).<br/><br/>"
            f"**Current average customer satisfaction: {outcome_display}**"
        )
        rec = (
            "Raising mandatory training completion is associated with better customer experience "
            "at the department level.<br/>"
            f"A 10-point increase in training completion is estimated to correlate with ~**{projected} points** "
            f"higher customer satisfaction."
        )
        metrics = [
            {"label": "Correlation Strength", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent"},
            {"label": "Average CSAT", "value": outcome_display, "sub": "across all departments", "theme": "warning"},
            {"label": "Driver", "value": "Training", "sub": "operational lever", "theme": "success"},
            {"label": "Impact", "value": "Service quality", "sub": "training → customer experience", "theme": "success"},
        ]
        return summary, rec, metrics

    direction = "positive" if r >= 0 else "negative"
    strongest_note = (
        " — the **strongest relationship on the dashboard**."
        if is_strongest
        else "."
    )
    summary = (
        f"Correlation between {driver_name} and {outcome_name} shows a **{strength}**, "
        f"{direction} relationship{strongest_note}<br/><br/>"
        f"**r = {r:.3f}**: as {driver_name} rises, {outcome_name} tends to "
        f"{'improve' if r >= 0 else 'decline'} across departments.<br/><br/>"
        f"**Current average {outcome_name}: {outcome_display}**"
    )
    rec = (
        f"Focus on improving {driver_name} may positively influence {outcome_name}.<br/>"
        f"A 10-point improvement in {driver_name} is estimated to correlate with ~**{projected} points** "
        f"change in {outcome_name}."
    )
    metrics = [
        {"label": "Correlation Strength", "value": f"r = {r:.3f}", "sub": pair_sub, "theme": "accent"},
        {"label": f"Average {outcome_name}", "value": outcome_display, "sub": "across all departments", "theme": "warning"},
        {"label": "Driver", "value": driver_name.split()[0] if driver_name else driver_name, "sub": "potential lever", "theme": "success"},
        {"label": "Impact", "value": "Linked", "sub": f"{driver_name} → {outcome_name}", "theme": "success"},
    ]
    return summary, rec, metrics


def build_correlation_context(analysis: QueryAnalysis, store=None) -> dict:
    """Structured correlation brief for API + UI (concise executive format)."""
    store = store or get_data_store()
    a, b = analysis.insights[0], analysis.insights[1]
    language = analysis.language
    branch = a.branch or "Network Average"

    dash_corr = lookup_dashboard_correlation(a.metric, b.metric, store)
    r = float(dash_corr["r"]) if dash_corr else _pearson_between(store, a.metric, b.metric, branch)
    if r is None:
        r = 0.0

    name_a = _display_name(a.metric, store)
    name_b = _display_name(b.metric, store)
    driver, outcome = _infer_driver_outcome(a, b)
    pair = _correlation_pair_key(a.metric, b.metric)

    driver_name = _friendly_metric_name(driver.metric, language, store)
    outcome_name = _friendly_metric_name(outcome.metric, language, store)

    outcome_avg = _dashboard_avg_for_metric(outcome.metric, store)
    if outcome_avg is None:
        outcome_avg = outcome.latest_value

    projected = round(10 * abs(r), 1)
    strength = _correlation_strength(r, language)
    is_strongest = _is_strongest_correlation(r, store)

    narrative_args = {
        "pair": pair,
        "driver_name": driver_name,
        "outcome_name": outcome_name,
        "r": r,
        "strength": strength,
        "is_strongest": is_strongest,
        "outcome_avg": outcome_avg,
        "outcome_metric": outcome.metric,
        "projected": projected,
    }
    if language == "ar":
        summary, rec, metrics = _build_correlation_narrative_ar(**narrative_args)
    else:
        summary, rec, metrics = _build_correlation_narrative_en(**narrative_args)

    return {
        "r": r,
        "branch": branch,
        "name_a": name_a,
        "name_b": name_b,
        "driver_name": driver_name,
        "outcome_name": outcome_name,
        "outcome_avg": outcome_avg,
        "summary": summary,
        "recommendation": rec,
        "metrics": metrics,
        "strength": strength,
    }


def _build_correlation_response(
    analysis: QueryAnalysis,
    store,
    source: str,
    language: str,
) -> ExecutiveResponse:
    ctx = build_correlation_context(analysis, store)
    a, b = analysis.insights[0], analysis.insights[1]
    name_a, name_b = ctx["name_a"], ctx["name_b"]
    r = ctx["r"]
    language = analysis.language

    if language == "ar":
        headline = f"تحليل الارتباط — {name_a} و{name_b}"
        corr_line = (
            f"معامل الارتباط = {r} ({ctx['strength']})"
            if r is not None
            else "تعذّر حساب معامل الارتباط."
        )
    else:
        headline = f"Correlation Analysis — {name_a} & {name_b}"
        corr_line = (
            f"Pearson r = {r} ({ctx['strength']})"
            if r is not None
            else "Could not compute correlation."
        )

    return ExecutiveResponse(
        headline=headline,
        executive_summary=ctx["summary"],
        key_findings=[],
        correlation_analysis=[corr_line],
        strategic_actions=[ctx["recommendation"]],
        data_citations=[f"{source} → Correlation_Data @ {ctx['branch']}"],
        chart_metrics=[a.metric, b.metric],
        language=language,
        grounded=True,
    )


def build_executive_response(analysis: QueryAnalysis) -> ExecutiveResponse:
    store = get_data_store()
    language = analysis.language
    source = store.source

    if not analysis.found:
        if language == "ar":
            msg = "تحليلي الحالي لقاعدة البيانات التشغيلية لا يحتوي على هذه المعلومات."
        else:
            msg = "My current analysis of the operational database does not contain this information."
        return ExecutiveResponse(
            headline="Data Not Available" if language == "en" else "البيانات غير متوفرة",
            executive_summary=msg,
            key_findings=[],
            correlation_analysis=[],
            strategic_actions=[],
            data_citations=[],
            chart_metrics=[],
            language=language,
            grounded=False,
        )

    if analysis.correlation_mode and len(analysis.insights) >= 2:
        return _build_correlation_response(analysis, store, source, language)

    findings: list[str] = []
    correlations: list[str] = []
    actions: list[str] = []
    citations: list[str] = []
    chart_metrics: list[str] = []

    primary = analysis.insights[0]
    for insight in analysis.insights:
        mm = store.metric_map[store.metric_map["metric_name"] == insight.metric]
        display = _display_name(insight.metric, store)
        formatted = _format_value(insight.metric, insight.latest_value)
        trend = _trend_label(insight.trend, language)

        finding = f"**{display}** ({insight.branch}, {insight.month}): {formatted} — {trend}"
        if insight.trend_pct is not None:
            suffix = " MoM" if language == "en" else ""
            finding += f" ({insight.trend_pct:+.1f}%{suffix})"

        if insight.is_risk and insight.risk_reason:
            finding += f" ⚠️ {insight.risk_reason}"
        findings.append(finding)
        citations.append(f"{source} → {insight.metric} @ {insight.branch}, {insight.month}")

        corr_text = _build_correlation_narrative(insight, language, store)
        if corr_text:
            if language == "ar":
                correlations.append(f"تحليل الارتباط لـ {display}: {corr_text}")
            else:
                correlations.append(f"Cross-metric analysis for {display}: {corr_text}")

        if insight.is_risk and not mm.empty:
            actions.append(str(mm.iloc[0]["suggested_action"]))
        elif not mm.empty and insight.trend in ("increasing", "decreasing"):
            actions.append(str(mm.iloc[0]["suggested_action"]))

        if analysis.wants_chart:
            chart_metrics.append(insight.metric)

    primary_display = _display_name(primary.metric, store)
    if language == "ar":
        headline = f"تقرير استراتيجي — {primary_display}"
        summary_parts = [
            f"بناءً على {source}، {primary_display} عند "
            f"{_format_value(primary.metric, primary.latest_value)} "
            f"({_trend_label(primary.trend, 'ar')})."
        ]
    else:
        headline = f"Strategic Brief — {primary_display}"
        summary_parts = [
            f"Based on {source}, {primary_display} stands at "
            f"{_format_value(primary.metric, primary.latest_value)} "
            f"({_trend_label(primary.trend, 'en')})."
        ]

    if primary.correlated:
        top = primary.correlated[0]
        top_name = _display_name(top["metric"], store)
        if language == "ar":
            summary_parts.append(
                f"يرتبط مع {top_name} (r={top.get('correlation', 'N/A')})."
            )
        else:
            summary_parts.append(
                f"Linked to {top_name} (r={top.get('correlation', 'N/A')})."
            )

    mm_primary = store.metric_map[store.metric_map["metric_name"] == primary.metric]
    if not mm_primary.empty:
        example = str(mm_primary.iloc[0].get("insight_example", ""))
        if example and example != "nan":
            summary_parts.append(example)

    executive_summary = " ".join(summary_parts)

    return ExecutiveResponse(
        headline=headline,
        executive_summary=executive_summary,
        key_findings=findings,
        correlation_analysis=correlations,
        strategic_actions=list(dict.fromkeys(a for a in actions if a and a != "nan")),
        data_citations=citations,
        chart_metrics=chart_metrics or [i.metric for i in analysis.insights],
        language=language,
        grounded=True,
    )
