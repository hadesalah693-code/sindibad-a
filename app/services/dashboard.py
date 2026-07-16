"""Dashboard KPIs and preset queries from Doha Oasis Excel workbook."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.data.loader import get_data_store


@dataclass
class DashboardKPIs:
    avoidable_costs_qar: float
    avoidable_costs_label: str
    exit_risk_count: int
    exit_risk_label: str
    exit_risk_label_en: str
    iso_readiness_pct: float
    iso_readiness_label: str
    employee_count: int
    department_count: int
    fiscal_year: str
    company_name: str
    company_name_en: str


@dataclass
class PresetQuestion:
    id: str
    title_ar: str
    title_en: str
    subtitle_ar: str
    subtitle_en: str
    query_ar: str
    query_en: str
    icon: str
    theme: str


def get_dashboard_kpis() -> DashboardKPIs:
    store = get_data_store()
    fin = store.finance
    emp = store.employees
    evidence = store.evidence_readiness

    avoidable = (
        float(fin["Turnover_Cost_QAR"].sum())
        + float(fin["Overtime_Cost_QAR"].sum())
        + float(fin["Recruitment_Cost_QAR"].sum())
    )
    high_risk = int((emp["Exit_Risk"].astype(str).str.lower() == "high").sum())
    iso_pct = round(float(evidence["Completeness %"].mean()) * 100)

    if avoidable >= 1_000_000:
        cost_label = f"{avoidable / 1_000_000:.1f}M QAR"
    else:
        cost_label = f"{avoidable:,.0f} QAR"

    return DashboardKPIs(
        avoidable_costs_qar=avoidable,
        avoidable_costs_label=cost_label,
        exit_risk_count=high_risk,
        exit_risk_label=f"{high_risk} موظف",
        exit_risk_label_en=f"{high_risk} employee{'s' if high_risk != 1 else ''}",
        iso_readiness_pct=iso_pct,
        iso_readiness_label=f"{iso_pct}%",
        employee_count=len(emp),
        department_count=int(emp["Department"].nunique()),
        fiscal_year="2025",
        company_name="شركة واحة الدوحة",
        company_name_en="Doha Oasis Company",
    )


def get_preset_questions() -> list[PresetQuestion]:
    return [
        PresetQuestion(
            id="costs",
            title_ar="ما هي التكاليف القابلة للتجنب في ميزانيتنا؟",
            title_en="What avoidable costs are in our budget?",
            subtitle_ar="تحليل التكاليف",
            subtitle_en="Cost Analysis",
            query_ar="ما هي التكاليف القابلة للتجنب في ميزانيتنا؟",
            query_en="What avoidable costs are in our budget?",
            icon="💰",
            theme="danger",
        ),
        PresetQuestion(
            id="exit_risk",
            title_ar="من الموظفون في خطر المغادرة المرتفع؟",
            title_en="Which employees are at high exit risk?",
            subtitle_ar="رصد مخاطر المغادرة",
            subtitle_en="Exit Risk Monitor",
            query_ar="من الموظفون في خطر المغادرة المرتفع؟",
            query_en="Which employees are at high exit risk?",
            icon="👤",
            theme="warning",
        ),
        PresetQuestion(
            id="iso",
            title_ar="ما مستوى استعدادنا لمعيار آيزو 30414؟",
            title_en="What is our ISO 30414 readiness level?",
            subtitle_ar="مؤشرات آيزو 30414",
            subtitle_en="ISO 30414 Indicators",
            query_ar="ما مستوى استعدادنا لمعيار آيزو 30414؟",
            query_en="What is our ISO 30414 readiness level?",
            icon="✓",
            theme="success",
        ),
    ]


_WORKBOOK_STAT_SPECS: list[tuple[str, str, str, str, str]] = [
    (
        "Average Engagement Score",
        "engagement",
        "متوسط الانخراط",
        "Avg Engagement",
        "score",
    ),
    (
        "Average Customer Satisfaction",
        "csat",
        "رضا العملاء",
        "Customer Satisfaction",
        "score",
    ),
    (
        "Average Employer Brand Score",
        "brand",
        "العلامة كصاحب عمل",
        "Employer Brand",
        "score",
    ),
    (
        "Average Training Completion",
        "training",
        "إكمال التدريب",
        "Training Completion",
        "pct",
    ),
    (
        "Average SLA Compliance",
        "sla",
        "الالتزام بـ SLA",
        "SLA Compliance",
        "pct",
    ),
    (
        "Average HC Impact Score",
        "hc_impact",
        "تأثير رأس المال البشري",
        "HC Impact Score",
        "score",
    ),
    (
        "Average Turnover Rate",
        "turnover",
        "معدل الدوران",
        "Turnover Rate",
        "pct",
    ),
    (
        "Total Revenue QAR",
        "revenue",
        "إجمالي الإيرادات",
        "Total Revenue",
        "qar",
    ),
]


def _format_workbook_stat(value: float, fmt: str) -> str:
    if fmt == "pct":
        return f"{value * 100:.1f}%"
    if fmt == "qar":
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M QAR"
        return f"{value:,.0f} QAR"
    if fmt == "score":
        if value <= 1:
            return f"{value * 100:.1f}%"
        return f"{value:.1f}"
    return f"{value:,.0f}"


def get_workbook_statistics() -> list[dict[str, Any]]:
    """Expose pre-computed KPIs from the Excel Dashboard sheet."""
    store = get_data_store()
    sheet_kpis = store.dashboard.get("kpis", {})
    stats: list[dict[str, Any]] = []

    for key, stat_id, label_ar, label_en, fmt in _WORKBOOK_STAT_SPECS:
        raw = sheet_kpis.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        stats.append(
            {
                "id": stat_id,
                "label_ar": label_ar,
                "label_en": label_en,
                "value": _format_workbook_stat(value, fmt),
                "source": "Dashboard",
            }
        )

    correlations = store.dashboard.get("correlations", [])
    if correlations:
        strongest = max(correlations, key=lambda c: abs(float(c.get("r", 0) or 0)))
        stats.append(
            {
                "id": "strongest_correlation",
                "label_ar": "أقوى ارتباط",
                "label_en": "Strongest Correlation",
                "value": f"r = {float(strongest['r']):+.2f}",
                "subtitle_ar": str(strongest.get("pair", "")),
                "subtitle_en": str(strongest.get("pair", "")),
                "source": "Dashboard",
            }
        )

    return stats


def _fmt_qar(amount: float) -> str:
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M QAR"
    return f"{amount:,.0f} QAR"


def _fmt_qar_ar(amount: float) -> str:
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M ريال"
    return f"{amount:,.0f} ريال"


def _fmt_qar_ar_full(amount: float) -> str:
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M ريال قطري"
    return f"{amount:,.0f} ريال قطري"


def _dept_letter(name: str) -> str:
    return (name.strip()[0] if name else "?").upper()


def _compute_risk_score(row: pd.Series) -> int:
    score = 55
    perf = float(row.get("Performance_Score", 3) or 3)
    eng = float(row.get("Engagement_Score", 50) or 50)
    if perf < 2.5:
        score += 18
    elif perf < 3.0:
        score += 14
    elif perf < 3.5:
        score += 8
    if eng < 45:
        score += 14
    elif eng < 50:
        score += 8
    sr = row.get("Successor_Ready")
    if pd.isna(sr) or str(sr).strip().lower() in ("", "no", "nan"):
        score += 12
    absence = float(row.get("Absence_Days_YTD", 0) or 0)
    if absence > 6:
        score += 6
    return min(98, max(72, int(score)))


def _exit_reasons(row: pd.Series, ar: bool) -> list[str]:
    reasons: list[str] = []
    sr = row.get("Successor_Ready")
    if pd.isna(sr) or str(sr).strip().lower() in ("", "no", "nan"):
        reasons.append("لا توجد خطة خلافة" if ar else "No succession plan")
    perf = float(row.get("Performance_Score", 3) or 3)
    if perf < 3.5:
        reasons.append(
            f"أداء دون المتوسط: {perf:.1f}/5" if ar else f"Performance below average: {perf:.1f}/5"
        )
    eng = float(row.get("Engagement_Score", 50) or 50)
    if eng < 50:
        reasons.append(
            f"مشاركة منخفضة: {eng:.0f}/100" if ar else f"Low engagement: {eng:.0f}/100"
        )
    absence = float(row.get("Absence_Days_YTD", 0) or 0)
    if absence > 6:
        reasons.append(
            f"غياب مرتفع: {absence:.0f} أيام" if ar else f"High absence: {absence:.0f} days"
        )
    return reasons[:3]


def _build_employee_alerts(high: pd.DataFrame, ar: bool) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    total = len(high)
    for i, (_, row) in enumerate(high.iterrows(), start=1):
        alerts.append(
            {
                "index": i,
                "total": total,
                "score": _compute_risk_score(row),
                "employee_id": str(row.get("Employee_ID", "")),
                "name": str(row.get("Employee_Name", "")),
                "department": str(row.get("Department", "")),
                "job_title": str(row.get("Job_Title", "")),
                "reasons": _exit_reasons(row, ar),
                "recommendation": (
                    "جدولة مقابلة احتفاظ هذا الأسبوع"
                    if ar
                    else "Schedule a retention interview this week"
                ),
            }
        )
    return alerts


def get_quick_tags() -> list[dict[str, str]]:
    return [
        {
            "label_ar": "التكاليف القابلة للتجنب",
            "label_en": "Avoidable Costs",
            "query_ar": "ما هي التكاليف القابلة للتجنب في ميزانيتنا؟",
            "query_en": "What avoidable costs are in our budget?",
        },
        {
            "label_ar": "مخاطر المغادرة",
            "label_en": "Exit Risk",
            "query_ar": "مخاطر مغادرة الموظفين",
            "query_en": "Which employees are at high exit risk?",
        },
        {
            "label_ar": "آيزو 30414",
            "label_en": "ISO 30414",
            "query_ar": "جاهزية آيزو 30414",
            "query_en": "What is our ISO 30414 readiness level?",
        },
        {
            "label_ar": "الانخراط والعلامة التجارية",
            "label_en": "Engagement & Brand",
            "query_ar": "ما العلاقة بين الانخراط الوظيفي والعلامة التجارية كصاحب عمل؟",
            "query_en": "What is the relationship between employee engagement and employer brand?",
        },
        {
            "label_ar": "رضا العملاء والتدريب",
            "label_en": "CSAT & Training",
            "query_ar": "ما العلاقة بين رضا العملاء وإكمال التدريب؟",
            "query_en": "What is the relationship between customer satisfaction and training completion?",
        },
        {
            "label_ar": "تحية",
            "label_en": "Greeting",
            "query_ar": "السلام عليكم",
            "query_en": "Hello",
        },
    ]


def _resolve_language(query: str, language: str | None) -> bool:
    """Return True for Arabic, False for English."""
    if language in ("ar", "en"):
        return language == "ar"
    return any("\u0600" <= c <= "\u06FF" for c in query)


def _is_greeting_query(query: str) -> bool:
    q = query.strip().lower()
    greetings = (
        "السلام عليكم",
        "سلام عليكم",
        "assalamu alaikum",
        "assalam alaikum",
        "salam alaikum",
        "hello",
        "good morning",
        "good afternoon",
        "good evening",
    )
    return any(g in q for g in greetings)


def _build_greeting_response(ar: bool) -> dict[str, Any]:
    kpis = get_dashboard_kpis()
    cost_label = kpis.avoidable_costs_label.replace(" QAR", " ريال") if ar else kpis.avoidable_costs_label
    exit_n = kpis.exit_risk_count
    iso_pct = kpis.iso_readiness_pct

    if ar:
        messages = [
            "وعليكم السلام، معاليكم 🌟",
            "أنا مستشارك الاستراتيجي الذكي لمنصة سندباد. لدي 3 رؤى عاجلة تستحق اهتمامك:",
            f"💰 **التكاليف القابلة للتجنب** — {cost_label} في تكاليف يمكن تفاديها",
            f"🚨 **مخاطر المغادرة** — {exit_n} موظف{'اً' if exit_n != 1 else ''} في خطر مغادرة مرتفع",
            f"📋 **آيزو 30414** — {iso_pct}٪ متوسط الجاهزية عبر جميع المجالات",
            "بأي منها تبدأ، معاليكم؟",
        ]
        headline = "تحية وتوجيه"
    else:
        messages = [
            "Hello — welcome to Sindibad 🌟",
            "I'm your strategic AI advisor. Here are 3 urgent insights worth your attention:",
            f"💰 **Avoidable costs** — {cost_label} in costs that can be reduced",
            f"🚨 **Exit risk** — {exit_n} employee{'s' if exit_n != 1 else ''} at high exit risk",
            f"📋 **ISO 30414** — {iso_pct}% average readiness across all areas",
            "Which would you like to start with?",
        ]
        headline = "Greeting & Briefing"

    return {
        "grounded": True,
        "language": "ar" if ar else "en",
        "response_type": "greeting",
        "headline": headline,
        "executive_summary": messages[0],
        "key_findings": [],
        "strategic_actions": [],
        "ui": {
            "theme": "accent",
            "layout": "greeting",
            "messages": messages,
        },
    }


def try_special_query(query: str, language: str | None = None) -> dict[str, Any] | None:
    """Answer preset dashboard questions directly from Excel sheets."""
    q = query.strip().lower()
    store = get_data_store()
    ar = _resolve_language(query, language)

    if _is_greeting_query(query):
        return _build_greeting_response(ar)

    # Avoidable costs
    if any(
        k in q
        for k in (
            "تكلف",
            "تكاليف",
            "للتجنب",
            "avoidable",
            "cost",
            "ميزان",
            "overtime",
            "turnover cost",
        )
    ):
        fin = store.finance
        turnover = float(fin["Turnover_Cost_QAR"].sum())
        overtime = float(fin["Overtime_Cost_QAR"].sum())
        recruit = float(fin["Recruitment_Cost_QAR"].sum())
        total = turnover + overtime + recruit
        by_dept = (
            fin.groupby("department")[["Turnover_Cost_QAR", "Overtime_Cost_QAR", "Recruitment_Cost_QAR"]]
            .sum()
            .assign(total=lambda d: d.sum(axis=1))
            .sort_values("total", ascending=False)
        )
        table_rows = []
        for dept, row in by_dept.head(6).iterrows():
            table_rows.append(
                {
                    "department": dept,
                    "turnover": round(row["Turnover_Cost_QAR"]),
                    "overtime": round(row["Overtime_Cost_QAR"]),
                    "recruitment": round(row["Recruitment_Cost_QAR"]),
                    "total": round(row["total"]),
                }
            )
        summary_ar = (
            "معاليكم، أجريت تحليلاً شاملاً للتكاليف القابلة للتجنب.<br/><br/>"
            f"⚠️ **الإجمالي: {_fmt_qar_ar_full(total)}** في تكاليف يمكن تفاديها.<br/><br/>"
            f"**التفاصيل:** دوران وظيفي {_fmt_qar_ar(turnover)} | "
            f"عمل إضافي {_fmt_qar_ar(overtime)} | "
            f"توظيف {_fmt_qar_ar(recruit)}"
        )
        summary_en = (
            "Your Excellency, I completed a full avoidable-cost analysis.<br/><br/>"
            f"⚠️ **Total: {_fmt_qar(total)}** in costs that can be avoided.<br/><br/>"
            f"**Breakdown:** Turnover {_fmt_qar(turnover)} | "
            f"Overtime {_fmt_qar(overtime)} | "
            f"Recruitment {_fmt_qar(recruit)}"
        )
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "costs",
            "headline": "تحليل التكاليف القابلة للتجنب" if ar else "Avoidable Cost Analysis",
            "executive_summary": summary_ar if ar else summary_en,
            "key_findings": [
                f"Turnover: {_fmt_qar(turnover)}" if not ar else f"دوران: {_fmt_qar(turnover)}",
                f"Overtime: {_fmt_qar(overtime)}" if not ar else f"عمل إضافي: {_fmt_qar(overtime)}",
                f"Recruitment: {_fmt_qar(recruit)}" if not ar else f"توظيف: {_fmt_qar(recruit)}",
            ],
            "table": table_rows,
            "chart": {
                "type": "bar",
                "title": (
                    "التكاليف القابلة للتجنب حسب الإدارة QAR"
                    if ar
                    else "Avoidable Cost by Department (QAR)"
                ),
                "labels": [r["department"] for r in table_rows],
                "values": [r["total"] for r in table_rows],
                "color": "#f87171",
            },
            "ui": {
                "theme": "danger",
                "layout": "costs_report",
                "hero": {
                    "label": "إجمالي" if ar else "Total",
                    "value": _fmt_qar(total),
                    "icon": "⚠",
                    "breakdown": (
                        f"{_fmt_qar(overtime)} عمل إضافي · {_fmt_qar(recruit)} توظيف · {_fmt_qar(turnover)} دوران"
                        if ar
                        else f"{_fmt_qar(overtime)} Overtime · {_fmt_qar(recruit)} Recruitment · {_fmt_qar(turnover)} Turnover"
                    ),
                },
                "list_title": (
                    f"الإدارات — التكاليف القابلة للتجنب: {_fmt_qar_ar(total)}"
                    if ar
                    else f"Departments — Avoidable Cost: {_fmt_qar(total)}"
                ),
                "list_items": [
                    {
                        "name": r["department"],
                        "value": _fmt_qar_ar(r["total"]) if ar else _fmt_qar(r["total"]),
                        "subtitle": r["department"],
                        "letter": _dept_letter(r["department"]),
                    }
                    for r in table_rows
                ],
                "metrics": [
                    {
                        "label": "دوران" if ar else "Turnover",
                        "value": _fmt_qar(turnover),
                        "sub": "تكلفة" if ar else "cost",
                        "theme": "danger",
                        "icon": "↻",
                    },
                    {
                        "label": "عمل إضافي" if ar else "Overtime",
                        "value": _fmt_qar(overtime),
                        "sub": "تكلفة" if ar else "cost",
                        "theme": "warning",
                        "icon": "⏱",
                    },
                    {
                        "label": "توظيف" if ar else "Recruitment",
                        "value": _fmt_qar(recruit),
                        "sub": "تكلفة" if ar else "cost",
                        "theme": "neutral",
                        "icon": "◎",
                    },
                ],
            },
            "strategic_actions": [
                "Strengthen workforce planning and absence management."
                if not ar
                else "تعزيز تخطيط القوى العاملة وإدارة الغياب.",
            ],
        }

    # Exit risk employees
    if any(k in q for k in ("مغادر", "exit risk", "attrition", "مخاطر مغادر")) or (
        "موظف" in q and any(k in q for k in ("مخاطر", "risk", "مغادر", "خط"))
    ):
        emp = store.employees
        high = emp[emp["Exit_Risk"].astype(str).str.lower() == "high"]
        medium = emp[emp["Exit_Risk"].astype(str).str.lower() == "medium"]
        table_rows = high[
            ["Employee_ID", "Employee_Name", "Department", "Job_Title", "Engagement_Score", "Performance_Score"]
        ].head(10).to_dict(orient="records")
        pct_at_risk = round((len(high) + len(medium)) / max(len(emp), 1) * 100)
        summary_ar = (
            f"اكتشف نظام رصد المواهب **{len(high)}** موظفين في خطر مغادرة مرتفع "
            f"بحاجة إلى تدخل فوري. كما أن **{len(medium)}** موظفاً في خطر متوسط — "
            f"**{pct_at_risk}%** من إجمالي القوى العاملة في خطر."
        )
        summary_en = (
            f"Talent monitoring detected **{len(high)}** employees at high exit risk "
            f"requiring immediate intervention. **{len(medium)}** are at medium risk — "
            f"**{pct_at_risk}%** of the workforce is at risk."
        )
        dept_high = high.groupby("Department").size()
        dept_med = medium.groupby("Department").size()
        all_depts = dept_high.add(dept_med, fill_value=0).sort_values(ascending=False).head(6)
        dept_labels = list(all_depts.index)
        employee_alerts = _build_employee_alerts(high, ar)
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "exit_risk",
            "headline": "رصد مخاطر المغادرة" if ar else "Exit Risk Monitor",
            "executive_summary": summary_ar if ar else summary_en,
            "key_findings": [f"{a['name']}: score {a['score']}" for a in employee_alerts],
            "table": table_rows,
            "chart": {
                "type": "grouped_bar",
                "title": (
                    "توزيع مخاطر المغادرة حسب الإدارة (موظفون)"
                    if ar
                    else "Exit Risk Distribution by Department"
                ),
                "labels": dept_labels,
                "series": [
                    {
                        "name": "خطر مرتفع" if ar else "High Risk",
                        "values": [int(dept_high.get(d, 0)) for d in dept_labels],
                        "color": "#ef4444",
                    },
                    {
                        "name": "خطر متوسط" if ar else "Medium Risk",
                        "values": [int(dept_med.get(d, 0)) for d in dept_labels],
                        "color": "#c9a66b",
                    },
                ],
            },
            "ui": {
                "theme": "danger",
                "layout": "employee_alerts",
                "hero": None,
                "list_items": [],
                "metrics": [],
                "stats": [
                    {"label": "خطر مرتفع" if ar else "High Risk", "value": str(len(high)), "theme": "danger"},
                    {"label": "خطر متوسط" if ar else "Medium", "value": str(len(medium)), "theme": "warning"},
                    {"label": "من القوى العاملة" if ar else "Of Workforce", "value": f"{pct_at_risk}%", "theme": "neutral"},
                ],
                "employee_alerts": employee_alerts,
                "actions": [
                    {
                        "label": "تطبيق برنامج الاحتفاظ" if ar else "Apply retention program",
                        "style": "outline",
                    },
                    {
                        "label": "جدولة مقابلات فردية" if ar else "Schedule individual interviews",
                        "style": "primary",
                    },
                ],
            },
            "strategic_actions": [],
        }

    # ISO 30414 readiness
    if any(k in q for k in ("30414", "iso", "آيزو", "evidence", "readiness", "استعداد")):
        evidence = store.evidence_readiness
        table_rows = evidence[
            ["ISO Area", "Completeness %", "Validation Status", "Risk Level"]
        ].to_dict(orient="records")
        avg = float(evidence["Completeness %"].mean()) * 100
        validated = int((evidence["Validation Status"] == "Validated").sum())
        in_progress = int((evidence["Validation Status"] == "In Progress").sum())
        high_risk = int((evidence["Risk Level"].astype(str).str.lower() == "high").sum())
        summary_ar = (
            f"مراجعة Evidence_Readiness تُظهر اكتمالاً متوسطاً بنسبة **{avg:.0f}%**. "
            f"**{high_risk}** مجالات عالية المخاطر تتطلب تدخلاً عاجلاً قبل المراجعة القادمة."
        )
        summary_en = (
            f"Evidence_Readiness review shows **{avg:.0f}%** average completeness. "
            f"**{high_risk}** high-risk areas require urgent intervention before the next review."
        )
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "iso",
            "headline": "جاهزية آيزو 30414" if ar else "ISO 30414 Readiness",
            "executive_summary": summary_ar if ar else summary_en,
            "key_findings": [
                f"{r['ISO Area']}: {float(r['Completeness %'])*100:.0f}% ({r['Validation Status']})"
                for r in table_rows
            ],
            "table": table_rows,
            "chart": {
                "type": "bar",
                "title": "اكتمال الأدلة %" if ar else "Evidence Completeness %",
                "labels": [r["ISO Area"] for r in table_rows],
                "values": [round(float(r["Completeness %"]) * 100, 1) for r in table_rows],
                "color": "#34d399",
            },
            "ui": {
                "theme": "success",
                "layout": "iso_compliance",
                "list_title": "ISO 30414 Readiness by Area",
                "list_items": [],
                "metrics": [
                    {
                        "label": "Average Readiness" if not ar else "متوسط الاستعداد",
                        "value": f"{avg:.0f}%",
                        "sub": "across all areas" if not ar else "عبر جميع المجالات",
                        "theme": "danger" if avg < 50 else "success",
                    },
                    {
                        "label": "Validated Areas" if not ar else "مجالات معتمدة",
                        "value": str(validated),
                        "sub": f"of {len(evidence)} total" if not ar else f"من {len(evidence)} إجمالي",
                        "theme": "success",
                    },
                    {
                        "label": "High-Risk Areas" if not ar else "مجالات عالية المخاطر",
                        "value": str(high_risk),
                        "sub": "urgent attention" if not ar else "تتطلب تدخلاً",
                        "theme": "danger",
                    },
                    {
                        "label": "In Progress" if not ar else "قيد التنفيذ",
                        "value": str(in_progress),
                        "sub": "being addressed" if not ar else "جاري معالجتها",
                        "theme": "warning",
                    },
                ],
                "table_meta": {
                    "title": "ISO 30414 Readiness by Area",
                    "badge": str(len(table_rows)),
                    "type": "iso",
                },
            },
            "strategic_actions": [
                "Automate reminders and escalation for incomplete policy acknowledgement."
                if not ar
                else "أتمتة التذكير والتصعيد لإقرار السياسات غير المكتمل.",
            ],
        }

    return None
