"""Doha Oasis SBU entity model — ISO 30414 readiness by business unit."""

from __future__ import annotations

from typing import Any

from app.data.loader import get_data_store

RAG_SCORES: dict[str, int] = {
    "green": 100,
    "amber": 60,
    "yellow": 60,
    "red": 0,
}

RAG_EMOJI: dict[str, str] = {
    "green": "🟢",
    "amber": "🟡",
    "yellow": "🟡",
    "red": "🔴",
}


def _rag_key(value: str) -> str:
    return str(value or "").strip().lower()


def _rag_score(value: str) -> int:
    return RAG_SCORES.get(_rag_key(value), 0)


def _rag_emoji(value: str) -> str:
    return RAG_EMOJI.get(_rag_key(value), "⚪")


def _rag_theme(value: str) -> str:
    key = _rag_key(value)
    if key == "green":
        return "success"
    if key in {"amber", "yellow"}:
        return "warning"
    if key == "red":
        return "danger"
    return "neutral"


def compute_sbu_readiness(store=None) -> list[dict[str, Any]]:
    """Average RAG score per SBU entity."""
    store = store or get_data_store()
    entities = store.entity_profile
    metrics = store.iso_metric_availability
    if entities.empty or metrics.empty:
        return []

    rows: list[dict[str, Any]] = []
    for _, entity in entities.iterrows():
        entity_id = str(entity["Entity_ID"])
        subset = metrics[metrics["Entity_ID"] == entity_id]
        if subset.empty:
            readiness = 0.0
            rag_label = "Red"
        else:
            scores = subset["RAG"].map(_rag_score)
            readiness = round(float(scores.mean()), 1)
            rag_label = "Green" if readiness >= 85 else "Amber" if readiness >= 65 else "Red"

        short_name = str(entity["SBU"]).split("&")[0].strip()
        if "Shared Services" in str(entity["SBU"]):
            short_name = "Shared Services"

        rows.append(
            {
                "entity_id": entity_id,
                "sbu": str(entity["SBU"]),
                "short_name": short_name,
                "example_head": str(entity.get("Example_Head", "")),
                "employees": int(entity.get("Employees", 0) or 0),
                "readiness_pct": readiness,
                "readiness_label": f"{readiness:.0f}%",
                "rag": rag_label,
                "rag_emoji": _rag_emoji(rag_label),
                "theme": _rag_theme(rag_label),
                "metric_count": int(len(subset)),
                "green_count": int((subset["RAG"].map(_rag_key) == "green").sum()) if len(subset) else 0,
                "amber_count": int(subset["RAG"].map(_rag_key).isin({"amber", "yellow"}).sum()) if len(subset) else 0,
                "red_count": int((subset["RAG"].map(_rag_key) == "red").sum()) if len(subset) else 0,
            }
        )

    rows.sort(key=lambda r: r["readiness_pct"], reverse=True)
    return rows


def get_corporate_iso_dashboard(store=None) -> dict[str, Any]:
    store = store or get_data_store()
    sbu_rows = compute_sbu_readiness(store)
    overall = round(sum(r["readiness_pct"] for r in sbu_rows) / max(len(sbu_rows), 1), 1)
    total_employees = int(store.entity_profile["Employees"].sum()) if not store.entity_profile.empty else 0

    gaps = sorted(sbu_rows, key=lambda r: r["readiness_pct"])
    return {
        "group": "Doha Oasis Group",
        "overall_readiness_pct": overall,
        "overall_readiness_label": f"{overall:.0f}%",
        "total_sbus": len(sbu_rows),
        "total_employees": total_employees,
        "sbu_readiness": sbu_rows,
        "largest_gap_sbu": gaps[0] if gaps else None,
        "best_sbu": sbu_rows[0] if sbu_rows else None,
    }


def get_entity_metrics(entity_id: str, store=None) -> list[dict[str, Any]]:
    store = store or get_data_store()
    subset = store.iso_metric_availability[
        store.iso_metric_availability["Entity_ID"] == entity_id
    ]
    evidence = store.evidence_repository

    rows: list[dict[str, Any]] = []
    for _, row in subset.iterrows():
        metric = str(row["ISO_Metric"])
        ev = evidence[
            (evidence["Entity_ID"] == entity_id) & (evidence["ISO_Metric"] == metric)
        ]
        rows.append(
            {
                "entity_id": entity_id,
                "iso_metric": metric,
                "source": str(row.get("Source", "")),
                "rag": str(row.get("RAG", "")),
                "rag_emoji": _rag_emoji(str(row.get("RAG", ""))),
                "owner": str(row.get("Owner", "")),
                "evidence_count": int(len(ev)),
                "evidence_files": ev["File_Name"].tolist() if not ev.empty else [],
            }
        )
    return rows


def find_sbu_by_name(text: str, store=None) -> dict[str, Any] | None:
    store = store or get_data_store()
    q = text.lower()
    for _, row in store.entity_profile.iterrows():
        sbu = str(row["SBU"]).lower()
        if str(row["Entity_ID"]).lower() in q or any(token in q for token in sbu.split() if len(token) > 3):
            return {
                "entity_id": str(row["Entity_ID"]),
                "sbu": str(row["SBU"]),
                "example_head": str(row.get("Example_Head", "")),
                "employees": int(row.get("Employees", 0) or 0),
            }
    aliases = {
        "banyan": "SBU001",
        "printemps": "SBU002",
        "quest": "SBU003",
        "novo": "SBU004",
        "cinema": "SBU004",
        "dining": "SBU005",
        "lifestyle": "SBU005",
        "shared services": "SBU006",
        "corporate": "SBU006",
    }
    for alias, entity_id in aliases.items():
        if alias in q:
            hit = store.entity_profile[store.entity_profile["Entity_ID"] == entity_id]
            if not hit.empty:
                row = hit.iloc[0]
                return {
                    "entity_id": entity_id,
                    "sbu": str(row["SBU"]),
                    "example_head": str(row.get("Example_Head", "")),
                    "employees": int(row.get("Employees", 0) or 0),
                }
    return None


def try_sbu_iso_query(query: str, language: str | None = None) -> dict[str, Any] | None:
    """Answer SBU / ISO 30414 entity-model questions."""
    q = query.strip().lower()
    ar = language == "ar" or (language is None and any("\u0600" <= c <= "\u06FF" for c in query))
    store = get_data_store()
    dashboard = get_corporate_iso_dashboard(store)

    triggers = (
        "sbu",
        "business unit",
        "وحدة أعمال",
        "banyan",
        "printemps",
        "quest",
        "novo",
        "dining",
        "shared services",
        "iso 30414 report",
        "corporate dashboard",
        "data gap",
        "evidence repository",
        "metric availability",
    )
    if not any(t in q for t in triggers):
        return None

    if any(k in q for k in ("corporate", "all sbu", "overall", "group", "كل الوحدات", "الإجمالي", "تقرير")):
        rows = dashboard["sbu_readiness"]
        summary_ar = (
            f"**{dashboard['overall_readiness_label']}** متوسط الجاهزية عبر **{dashboard['total_sbus']}** وحدات أعمال "
            f"({dashboard['total_employees']:,} موظف). "
            f"أكبر فجوة: **{dashboard['largest_gap_sbu']['sbu']}** ({dashboard['largest_gap_sbu']['readiness_label']})."
        )
        summary_en = (
            f"**{dashboard['overall_readiness_label']}** overall readiness across **{dashboard['total_sbus']}** SBUs "
            f"({dashboard['total_employees']:,} employees). "
            f"Largest gap: **{dashboard['largest_gap_sbu']['sbu']}** ({dashboard['largest_gap_sbu']['readiness_label']})."
        )
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "sbu_iso",
            "headline": "Corporate ISO 30414 Readiness" if not ar else "جاهزية آيزو 30414 على مستوى المجموعة",
            "executive_summary": summary_ar if ar else summary_en,
            "table": rows,
            "ui": {
                "theme": "success",
                "layout": "sbu_readiness",
                "metrics": [
                    {
                        "label": "Overall Readiness" if not ar else "الجاهزية الإجمالية",
                        "value": dashboard["overall_readiness_label"],
                        "sub": "Doha Oasis Group" if not ar else "مجموعة واحة الدوحة",
                        "theme": "success" if dashboard["overall_readiness_pct"] >= 75 else "warning",
                    },
                    {
                        "label": "SBUs" if not ar else "وحدات الأعمال",
                        "value": str(dashboard["total_sbus"]),
                        "sub": "Entity_Profile" if not ar else "جدول الكيانات",
                        "theme": "neutral",
                    },
                    {
                        "label": "Largest Gap" if not ar else "أكبر فجوة",
                        "value": dashboard["largest_gap_sbu"]["short_name"] if dashboard["largest_gap_sbu"] else "—",
                        "sub": dashboard["largest_gap_sbu"]["readiness_label"] if dashboard["largest_gap_sbu"] else "",
                        "theme": "danger",
                    },
                ],
                "list_items": [
                    {
                        "name": r["short_name"],
                        "subtitle": r["sbu"],
                        "value": f"{r['rag_emoji']} {r['readiness_label']}",
                        "letter": r["entity_id"][-1],
                        "theme": r["theme"],
                    }
                    for r in rows
                ],
                "list_title": "SBU Readiness" if not ar else "جاهزية الوحدات",
            },
        }

    if any(k in q for k in ("largest gap", "data gap", "missing", "أكبر فجوة", "فجوات", "ناقص")):
        worst = dashboard["largest_gap_sbu"]
        if not worst:
            return None
        metrics = get_entity_metrics(worst["entity_id"], store)
        missing = [m for m in metrics if _rag_key(m["rag"]) == "red"]
        partial = [m for m in metrics if _rag_key(m["rag"]) in {"amber", "yellow"}]
        summary_ar = (
            f"**{worst['sbu']}** لديها أقل جاهزية ({worst['readiness_label']}). "
            f"مؤشرات حمراء: {len(missing)} | كهرمانية: {len(partial)}."
        )
        summary_en = (
            f"**{worst['sbu']}** has the lowest readiness ({worst['readiness_label']}). "
            f"Red metrics: {len(missing)} | Amber metrics: {len(partial)}."
        )
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "sbu_iso",
            "headline": "Largest ISO Data Gaps" if not ar else "أكبر فجوات بيانات آيزو",
            "executive_summary": summary_ar if ar else summary_en,
            "table": metrics,
            "ui": {
                "theme": "danger",
                "layout": "iso_compliance",
                "list_items": [
                    {
                        "name": m["iso_metric"],
                        "subtitle": f"{m['source']} · {m['owner']}",
                        "value": f"{m['rag_emoji']} {m['rag']}",
                        "letter": m["iso_metric"][:1],
                        "theme": _rag_theme(m["rag"]),
                    }
                    for m in sorted(metrics, key=lambda x: _rag_score(x["rag"]))
                ],
                "list_title": worst["sbu"],
            },
        }

    entity = find_sbu_by_name(q, store)
    if entity:
        metrics = get_entity_metrics(entity["entity_id"], store)
        red = [m for m in metrics if _rag_key(m["rag"]) == "red"]
        summary_ar = (
            f"**{entity['sbu']}** ({entity['entity_id']}) — {entity['employees']} موظف. "
            f"**{len(red)}** مؤشرات حمراء من أصل {len(metrics)}."
        )
        summary_en = (
            f"**{entity['sbu']}** ({entity['entity_id']}) — {entity['employees']} employees. "
            f"**{len(red)}** red metrics out of {len(metrics)}."
        )
        return {
            "grounded": True,
            "language": "ar" if ar else "en",
            "response_type": "sbu_iso",
            "headline": entity["sbu"],
            "executive_summary": summary_ar if ar else summary_en,
            "table": metrics,
            "ui": {
                "theme": "warning" if red else "success",
                "layout": "iso_compliance",
                "list_items": [
                    {
                        "name": m["iso_metric"],
                        "subtitle": (
                            f"{m['evidence_count']} evidence file(s)"
                            if not ar
                            else f"{m['evidence_count']} ملف(ات) دليل"
                        ),
                        "value": f"{m['rag_emoji']} {m['rag']}",
                        "letter": m["owner"][:1],
                        "theme": _rag_theme(m["rag"]),
                    }
                    for m in metrics
                ],
                "list_title": "ISO Metric Availability" if not ar else "توفر مؤشرات آيزو",
            },
        }

    return None
