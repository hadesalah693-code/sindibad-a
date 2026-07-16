"""Data loading utilities for Sindibad operational datasets (Excel / CSV)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.config import settings

EXCEL_FILE = "Doha_Oasis_Sindibad_Database.xlsx"
EXCEL_SHEETS = {
    "correlation": "Correlation_Data",
    "hr": "Monthly_HR",
    "finance": "Finance",
    "metric_map": "Metric_Map",
    "brand": "Brand",
    "customer_ops": "Customer_Ops",
    "employees": "Employees",
    "evidence": "Evidence_Readiness",
    "dashboard": "Dashboard",
    "lists": "Lists",
}

# Business KPI / driver labels → Correlation_Data column names
KPI_COLUMN_MAP: dict[str, str] = {
    "revenue": "Revenue_QAR",
    "revenue qar": "Revenue_QAR",
    "revenue per employee": "Revenue_Per_Employee",
    "overtime cost": "Overtime_Cost_QAR",
    "turnover cost": "Turnover_Cost_QAR",
    "employer brand score": "Employer_Brand_Score",
    "customer satisfaction": "Customer_Satisfaction",
    "complaint rate": "Complaint_Rate",
    "sla compliance": "SLA_Compliance",
    "compliance readiness": "Policy_Acknowledgement_Rate",
    "human capital impact score": "Composite_HC_Impact_Score",
    "localisation / qatarisation": "Succession_Coverage",
}

DRIVER_COLUMN_MAP: dict[str, str] = {
    "engagement score": "Engagement_Score",
    "engagement": "Engagement_Score",
    "absence rate": "Absence_Rate",
    "vacancy rate": "Vacancy_Rate",
    "turnover rate": "Turnover_Rate",
    "training completion": "Training_Completion_Rate",
    "training completion rate": "Training_Completion_Rate",
    "offer acceptance": "Offer_Acceptance_Rate",
    "offer acceptance rate": "Offer_Acceptance_Rate",
    "policy acknowledgement": "Policy_Acknowledgement_Rate",
    "mandatory training": "Mandatory_Training_Completion",
    "succession": "Succession_Coverage",
    "skills gap": "Vacancy_Rate",
    "workforce composition": "Succession_Coverage",
    "development": "Training_Completion_Rate",
}

HIGHER_IS_BETTER = {
    "Revenue_QAR",
    "Revenue_Per_Employee",
    "Engagement_Score",
    "Training_Completion_Rate",
    "SLA_Compliance",
    "Customer_Satisfaction",
    "Employer_Brand_Score",
    "Offer_Acceptance_Rate",
    "Human_Capital_ROI",
    "Composite_HC_Impact_Score",
    "Succession_Coverage",
    "Policy_Acknowledgement_Rate",
    "Mandatory_Training_Completion",
}

LOWER_IS_BETTER = {
    "Turnover_Rate",
    "Absence_Rate",
    "Vacancy_Rate",
    "Complaint_Rate",
    "Operational_Risk_Score",
    "Service_Backlog",
    "Overtime_Cost_QAR",
    "Turnover_Cost_QAR",
}


@dataclass(frozen=True)
class DataStore:
    """In-memory store of operational datasets loaded at startup."""

    correlation: pd.DataFrame
    hr: pd.DataFrame
    finance: pd.DataFrame
    metric_map: pd.DataFrame
    brand: pd.DataFrame
    customer_ops: pd.DataFrame
    employees: pd.DataFrame
    evidence_readiness: pd.DataFrame
    lists: pd.DataFrame
    dashboard: dict
    loaded_at: str
    source: str
    source_path: str
    org_unit_col: str = "department"

    @property
    def all_metric_columns(self) -> set[str]:
        exclude = {
            "month",
            "department",
            "branch",
            "metric_id",
            "metric_name",
            "metric_name_ar",
            "display_name",
            "business_area",
        }
        cols: set[str] = set()
        for frame in (self.correlation, self.hr, self.finance, self.brand, self.customer_ops):
            cols.update(c for c in frame.columns if c not in exclude)
        return cols


_store: DataStore | None = None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename = {}
    for col in df.columns:
        if col.lower() == "month":
            rename[col] = "month"
        elif col.lower() in {"department", "branch"}:
            rename[col] = "department"
    if rename:
        df = df.rename(columns=rename)
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"])
    return df


def _label_to_column(label: str) -> str | None:
    key = label.strip().lower()
    if key in KPI_COLUMN_MAP:
        return KPI_COLUMN_MAP[key]
    if key in DRIVER_COLUMN_MAP:
        return DRIVER_COLUMN_MAP[key]
    # Try partial match
    for pattern, col in {**KPI_COLUMN_MAP, **DRIVER_COLUMN_MAP}.items():
        if pattern in key or key in pattern:
            return col
    # Already a column-style name
    candidate = label.strip().replace(" ", "_")
    return candidate if candidate else None


def _parse_drivers(text: str) -> list[str]:
    if not text or pd.isna(text):
        return []
    parts = re.split(r"\+|,|\band\b", str(text), flags=re.IGNORECASE)
    columns: list[str] = []
    for part in parts:
        col = _label_to_column(part)
        if col and col not in columns:
            columns.append(col)
    return columns


def _normalize_metric_map(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in raw.iterrows():
        kpi = str(row.get("Business KPI", "")).strip()
        drivers = str(row.get("Human Capital Driver", "")).strip()
        metric_col = _label_to_column(kpi)
        if not metric_col:
            continue
        correlated = _parse_drivers(drivers)
        if metric_col in HIGHER_IS_BETTER:
            risk_direction = "below"
        elif metric_col in LOWER_IS_BETTER:
            risk_direction = "above"
        else:
            risk_direction = "below"

        rows.append(
            {
                "metric_name": metric_col,
                "display_name": kpi,
                "business_area": row.get("Business Area", ""),
                "correlated_metrics": ",".join(correlated),
                "correlation_logic": row.get("Correlation Logic", ""),
                "insight_example": row.get("Sindibad Insight Example", ""),
                "suggested_action": row.get("Suggested Action", ""),
                "risk_direction": risk_direction,
            }
        )
    return pd.DataFrame(rows)


# Dashboard sheet labels → canonical metric columns (for correlation lookup)
DASHBOARD_METRIC_TOKENS: dict[str, list[str]] = {
    "Engagement_Score": ["engagement"],
    "Employer_Brand_Score": ["employer brand", "brand score", "brand"],
    "Revenue_Per_Employee": ["revenue / employee", "revenue per employee"],
    "Training_Completion_Rate": ["training completion", "training"],
    "Customer_Satisfaction": ["customer satisfaction", "csat"],
    "Turnover_Rate": ["turnover rate", "turnover"],
    "Complaint_Rate": ["complaint rate", "complaint"],
    "Absence_Rate": ["absence rate", "absence"],
    "SLA_Compliance": ["sla compliance", "sla"],
    "Vacancy_Rate": ["vacancy rate", "vacancy"],
    "Service_Backlog": ["service backlog", "backlog"],
    "Composite_HC_Impact_Score": ["hc impact score", "hc impact"],
    "Human_Capital_ROI": ["human capital roi", "hc roi"],
}


def _parse_dashboard_sheet(raw: pd.DataFrame) -> dict:
    """Parse pre-computed KPIs and correlations from the Excel Dashboard sheet."""
    kpis: dict[str, float] = {}
    correlations: list[dict[str, str | float]] = []
    departments: list[dict[str, float | str]] = []
    recommendations: list[dict[str, str]] = []

    for i in range(3, 14):
        if i >= len(raw):
            break
        row = raw.iloc[i]
        kpi_name = row.iloc[0] if len(row) > 0 else None
        kpi_val = row.iloc[1] if len(row) > 1 else None
        if pd.notna(kpi_name) and pd.notna(kpi_val):
            try:
                kpis[str(kpi_name).strip()] = float(kpi_val)
            except (TypeError, ValueError):
                pass
        pair = row.iloc[3] if len(row) > 3 else None
        corr_val = row.iloc[4] if len(row) > 4 else None
        if pd.notna(pair) and pd.notna(corr_val):
            try:
                correlations.append(
                    {"pair": str(pair).strip(), "r": round(float(corr_val), 3)}
                )
            except (TypeError, ValueError):
                pass

    if len(raw) > 16:
        dept_header = [str(c).strip() for c in raw.iloc[15].tolist() if pd.notna(c)]
        for i in range(16, len(raw)):
            row = raw.iloc[i]
            if pd.isna(row.iloc[0]):
                break
            name = str(row.iloc[0]).strip()
            if name.lower().startswith("recommended"):
                break
            entry: dict[str, float | str] = {"department": name}
            for j, col in enumerate(dept_header[1:], start=1):
                if j < len(row) and pd.notna(row.iloc[j]):
                    try:
                        entry[col.lower()] = float(row.iloc[j])
                    except (TypeError, ValueError):
                        entry[col.lower()] = str(row.iloc[j])
            departments.append(entry)

    for i in range(len(raw)):
        cell = str(raw.iloc[i, 0]) if len(raw.iloc[i]) > 0 else ""
        if cell.strip().lower() == "recommended sindibad insight":
            for j in range(i + 1, len(raw)):
                row = raw.iloc[j]
                insight = row.iloc[0] if len(row) > 0 else None
                trigger = row.iloc[1] if len(row) > 1 else None
                action = row.iloc[2] if len(row) > 2 else None
                if pd.isna(insight):
                    break
                recommendations.append(
                    {
                        "insight": str(insight).strip(),
                        "trigger": str(trigger).strip() if pd.notna(trigger) else "",
                        "action": str(action).strip() if pd.notna(action) else "",
                    }
                )
            break

    return {
        "kpis": kpis,
        "correlations": correlations,
        "departments": departments,
        "recommendations": recommendations,
    }


def lookup_dashboard_correlation(
    metric_a: str,
    metric_b: str,
    store: DataStore | None = None,
) -> dict[str, str | float] | None:
    """Find pre-computed correlation r from Excel Dashboard sheet."""
    store = store or get_data_store()
    tokens_a = DASHBOARD_METRIC_TOKENS.get(metric_a, [metric_a.replace("_", " ").lower()])
    tokens_b = DASHBOARD_METRIC_TOKENS.get(metric_b, [metric_b.replace("_", " ").lower()])

    for entry in store.dashboard.get("correlations", []):
        pair = str(entry["pair"]).lower()
        a_ok = any(t in pair for t in tokens_a)
        b_ok = any(t in pair for t in tokens_b)
        if a_ok and b_ok:
            return entry
    return None


def get_dashboard_kpi(label: str, store: DataStore | None = None) -> float | None:
    """Read a KPI value pre-computed in the Excel Dashboard sheet."""
    store = store or get_data_store()
    val = store.dashboard.get("kpis", {}).get(label)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _load_excel(path: Path) -> DataStore:
    xls = pd.ExcelFile(path)
    correlation = _normalize_columns(pd.read_excel(xls, EXCEL_SHEETS["correlation"]))
    hr = _normalize_columns(pd.read_excel(xls, EXCEL_SHEETS["hr"]))
    finance = _normalize_columns(pd.read_excel(xls, EXCEL_SHEETS["finance"]))
    brand = _normalize_columns(pd.read_excel(xls, EXCEL_SHEETS["brand"]))
    customer_ops = _normalize_columns(pd.read_excel(xls, EXCEL_SHEETS["customer_ops"]))
    employees = pd.read_excel(xls, EXCEL_SHEETS["employees"])
    metric_map = _normalize_metric_map(pd.read_excel(xls, EXCEL_SHEETS["metric_map"]))
    evidence_readiness = pd.read_excel(xls, EXCEL_SHEETS["evidence"])
    lists = pd.read_excel(xls, EXCEL_SHEETS["lists"])
    dashboard_raw = pd.read_excel(xls, EXCEL_SHEETS["dashboard"], header=None)
    dashboard = _parse_dashboard_sheet(dashboard_raw)

    # Enrich correlation with finance-only columns for cross-table queries
    finance_cols = ["Overtime_Cost_QAR", "Turnover_Cost_QAR"]
    merge_cols = ["month", "department"] + [c for c in finance_cols if c in finance.columns]
    if all(c in finance.columns for c in ["month", "department"]):
        correlation = correlation.merge(
            finance[merge_cols],
            on=["month", "department"],
            how="left",
            suffixes=("", "_fin"),
        )

    loaded_at = pd.Timestamp.now("UTC").isoformat()
    return DataStore(
        correlation=correlation,
        hr=hr,
        finance=finance,
        metric_map=metric_map,
        brand=brand,
        customer_ops=customer_ops,
        employees=employees,
        evidence_readiness=evidence_readiness,
        lists=lists,
        dashboard=dashboard,
        loaded_at=loaded_at,
        source=str(path.name),
        source_path=str(path.resolve()),
    )


def load_data(data_dir: Path | None = None) -> DataStore:
    """Load Doha Oasis Excel workbook into a DataStore."""
    global _store
    base = data_dir or settings.data_dir
    excel_path = base / EXCEL_FILE
    if not excel_path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {excel_path}. "
            "Place Doha_Oasis_Sindibad_Database.xlsx in the data/ folder."
        )
    _store = _load_excel(excel_path)
    return _store


def get_data_store() -> DataStore:
    """Return the singleton DataStore, loading if necessary."""
    global _store
    if _store is None:
        return load_data()
    return _store


def get_risk_direction(metric: str) -> str | None:
    if metric in HIGHER_IS_BETTER:
        return "below"
    if metric in LOWER_IS_BETTER:
        return "above"
    return None
