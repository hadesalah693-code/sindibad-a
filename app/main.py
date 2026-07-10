"""FastAPI backend + executive dashboard for Sindibad."""

from __future__ import annotations

import logging
import os
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.sindibad_agent import AgentResult, SindibadAgent
from app.config import settings
from app.data.loader import get_data_store, load_data
from app.services.dashboard import (
    get_dashboard_kpis,
    get_preset_questions,
    get_quick_tags,
    try_special_query,
)

logger = logging.getLogger("sindibad")
_agent: SindibadAgent | None = None
STATIC_DIR = Path(__file__).resolve().parent / "static"
_ON_VERCEL = bool(os.environ.get("VERCEL"))


def _ensure_agent() -> SindibadAgent:
    """Lazy init for serverless (Vercel) where lifespan may not run."""
    global _agent
    if _agent is None:
        load_data()
        _agent = SindibadAgent()
    return _agent


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Executive Strategic AI Advisor — Doha Oasis Company",
)

if STATIC_DIR.exists() and not _ON_VERCEL:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    detail = str(exc) if _ON_VERCEL else traceback.format_exc()
    return JSONResponse(status_code=500, content={"detail": detail, "path": request.url.path})


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    include_charts: bool = True
    language: str = Field(default="ar", pattern="^(ar|en)$")


def _special_to_payload(special: dict[str, Any], query: str) -> dict[str, Any]:
    return {
        "query": query,
        "headline": special["headline"],
        "executive_summary": special["executive_summary"],
        "key_findings": special.get("key_findings", []),
        "correlation_analysis": [],
        "strategic_actions": special.get("strategic_actions", []),
        "grounded": True,
        "charts": [],
        "simple_chart": special.get("chart"),
        "table": special.get("table"),
        "ui": special.get("ui"),
        "response_type": special.get("response_type", "generic"),
        "display_markdown": _format_special_markdown(special),
        "metadata": {"type": "special_query", "language": special.get("language", "ar")},
    }


def _format_special_markdown(special: dict[str, Any]) -> str:
    lines = [f"## {special['headline']}", "", special["executive_summary"], ""]
    if special.get("key_findings"):
        lines.append("**أهم النتائج**" if special.get("language") == "ar" else "**Key Findings**")
        for f in special["key_findings"]:
            lines.append(f"- {f}")
        lines.append("")
    if special.get("strategic_actions"):
        lines.append("**التوصية**" if special.get("language") == "ar" else "**Recommendation**")
        for a in special["strategic_actions"]:
            lines.append(f"> {a}")
    return "\n".join(lines)


def _result_to_payload(result: AgentResult) -> dict[str, Any]:
    r = result.response
    agent = _agent
    display = agent.format_for_display(result) if agent else r.executive_summary
    charts_meta = [{"title": a.title, "figure": a.figure} for a in result.chart_artifacts]
    analysis = result.analysis
    correlation_mode = bool(analysis and analysis.correlation_mode)

    payload: dict[str, Any] = {
        "query": result.query,
        "headline": r.headline,
        "executive_summary": r.executive_summary,
        "key_findings": r.key_findings,
        "correlation_analysis": r.correlation_analysis,
        "strategic_actions": r.strategic_actions,
        "grounded": r.grounded,
        "charts": result.charts,
        "charts_meta": charts_meta,
        "display_markdown": display,
        "response_type": "correlation" if correlation_mode else "generic",
        "metadata": {
            **result.metadata,
            "correlation_mode": correlation_mode,
        },
    }

    if correlation_mode and analysis and len(analysis.insights) >= 2:
        from app.services.narrative import build_correlation_context

        store = agent.store if agent else load_data()
        ctx = build_correlation_context(analysis, store)
        payload["ui"] = {
            "theme": "success",
            "layout": "correlation",
            "show_chart": False,
            "metrics": ctx["metrics"],
            "recommendation_html": ctx["recommendation"],
        }

    return payload


@app.get("/")
async def dashboard_home():
    if _ON_VERCEL:
        raise HTTPException(
            status_code=404,
            detail="Dashboard UI is served from public/ on Vercel.",
        )
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    return FileResponse(index)


@app.get("/api/v1/dashboard")
async def dashboard_data():
    load_data()
    kpis = get_dashboard_kpis()
    return {
        "company": {
            "name_ar": kpis.company_name,
            "name_en": kpis.company_name_en,
            "fiscal_year": kpis.fiscal_year,
            "employees": kpis.employee_count,
            "departments": kpis.department_count,
            "data_source": get_data_store().source,
        },
        "kpis": [
            {
                "id": "costs",
                "label_ar": "التكاليف القابلة للتجنب",
                "label_en": "Avoidable Costs",
                "value": kpis.avoidable_costs_label,
                "theme": "danger",
            },
            {
                "id": "exit_risk",
                "label_ar": "موظفون في خطر مغادرة",
                "label_en": "Employees at exit risk",
                "value_ar": kpis.exit_risk_label,
                "value_en": kpis.exit_risk_label_en,
                "theme": "warning",
            },
            {
                "id": "iso",
                "label_ar": "جاهزية آيزو 30414",
                "label_en": "ISO 30414 Readiness",
                "value": kpis.iso_readiness_label,
                "theme": "success",
            },
        ],
        "preset_questions": [
            {
                "id": q.id,
                "title_ar": q.title_ar,
                "title_en": q.title_en,
                "subtitle_ar": q.subtitle_ar,
                "subtitle_en": q.subtitle_en,
                "query_ar": q.query_ar,
                "query_en": q.query_en,
                "icon": q.icon,
                "theme": q.theme,
            }
            for q in get_preset_questions()
        ],
        "quick_tags": get_quick_tags(),
    }


@app.post("/api/v1/advise")
async def advise(request: QueryRequest):
    agent = _ensure_agent()

    special = try_special_query(request.query, language=request.language)
    if special:
        return _special_to_payload(special, request.query)

    result = agent.ask(request.query, include_charts=request.include_charts)
    return _result_to_payload(result)


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "app": settings.app_name, "vercel": _ON_VERCEL}


@app.get("/health")
async def health():
    store = _ensure_agent().store
    return {
        "status": "healthy",
        "app": settings.app_name,
        "records": len(store.correlation),
        "source": store.source,
        "source_path": store.source_path,
        "data_dir": str(settings.data_dir),
        "sheets_loaded": [
            "Correlation_Data", "Monthly_HR", "Finance", "Metric_Map",
            "Brand", "Customer_Ops", "Employees", "Evidence_Readiness", "Dashboard",
        ],
    }


@app.get("/api/v1/metrics")
async def list_metrics():
    mm = _ensure_agent().store.metric_map
    return [
        {
            "name": row["metric_name"],
            "display_name": row.get("display_name", row["metric_name"]),
            "business_area": row.get("business_area", ""),
        }
        for _, row in mm.iterrows()
    ]
