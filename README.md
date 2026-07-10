# Sindibad — Executive Strategic AI Advisor

Virtual Strategic Advisor MVP for **Al Khebra Driving School**. Sindibad analyzes integrated workforce, financial, and operational CSV data to deliver predictive and prescriptive CEO-level insights.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12) |
| Data | Pandas |
| Agent Flow | LangGraph |
| UI | Chainlit + Plotly |

## Quick Start

**Requires Python 3.10–3.13 for Chainlit.** Python 3.14 needs the included patch (applied automatically by `run.ps1`).

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch Executive Dashboard (recommended)
.\run.ps1
# Opens http://localhost:8002

# Or Chainlit chat UI:
# .\run.ps1 chainlit

# 4. (Optional) Launch FastAPI backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Data Source

Primary data file: `data/Doha_Oasis_Sindibad_Database.xlsx` (Doha Oasis Company dummy correlation database).

| Sheet | Role |
|-------|------|
| `Correlation_Data` | Primary fact table |
| `Metric_Map` | KPI ↔ human capital driver logic & actions |
| `Monthly_HR` | Workforce metrics by department |
| `Finance` | Financial metrics by department |
| `Brand` / `Customer_Ops` / `Employees` | Supporting datasets |

## API

```bash
POST /api/v1/advise
{
  "query": "How is Revenue trending at Doha Central?",
  "include_charts": true
}
```

## Architecture

```
app/
├── agent/          # SindibadAgent + LangGraph workflow
├── data/           # CSV loader (Adler ERP-ready abstraction)
├── services/       # Analysis, narrative, charts
└── main.py         # FastAPI entry point
chainlit_app.py     # Executive chat UI
```

## Safety Guardrails

If a query cannot be answered from the operational database, Sindibad responds:

> *My current analysis of the operational database does not contain this information.*

No hallucinated metrics or fabricated numbers.

## Tests

```bash
pytest tests/ -v
```
