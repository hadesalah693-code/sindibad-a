# Doha Oasis Data Model — SBU Entity Relationships

Sindibad uses **Doha Oasis SBUs** as the primary business entities for ISO 30414 readiness, linked to operational correlation data in the Excel workbook.

```
                    DOHA OASIS GROUP
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
     ▼                     ▼                     ▼
Entity_Profile        ISO_Metric_Availability    Evidence_Repository
 (Master Table)          (Transaction Table)      (Documents / Files)
```

## 1. Entity_Profile (Master)

**File:** `data/Entity_Profile.csv`

| Column | Description |
|--------|-------------|
| Entity_ID | Stable SBU key (e.g. SBU001) |
| SBU | Business unit name |
| Example_Head | Typical executive owner |
| Employees | Headcount for weighting / context |

| Entity_ID | SBU | Example Head | Employees |
|-----------|-----|--------------|-----------|
| SBU001 | Banyan Tree Hotel & Residences | Hotel GM | 430 |
| SBU002 | Printemps Doha | Retail Director | 780 |
| SBU003 | Quest Theme Park | Park Director | 310 |
| SBU004 | Novo Cinemas | Cinema Manager | 140 |
| SBU005 | Dining & Lifestyle | F&B Director | 360 |
| SBU006 | Corporate Shared Services | COO | 220 |

**Relationship:** `Entity_ID` → one-to-many rows in `ISO_Metric_Availability` and `Evidence_Repository`.

---

## 2. ISO_Metric_Availability (Transaction)

**File:** `data/ISO_Metric_Availability.csv`

| Column | Description |
|--------|-------------|
| Entity_ID | FK → Entity_Profile |
| ISO_Metric | ISO 30414 metric name |
| Source | System of record (Oracle HR, LMS, ERP, …) |
| RAG | Green / Amber / Red availability |
| Owner | Accountable function (HR, Finance, HSE, …) |

### RAG rules

| RAG | Meaning | Score |
|-----|---------|-------|
| 🟢 Green | Complete and validated | 100 |
| 🟡 Amber | Data exists but incomplete or needs cleansing | 60 |
| 🔴 Red | Missing or unavailable | 0 |

**SBU readiness** = average RAG score per `Entity_ID`.

**Corporate readiness** = average of all SBU readiness scores.

---

## 3. Evidence_Repository (Audit trail)

**File:** `data/Evidence_Repository.csv`

| Column | Description |
|--------|-------------|
| Evidence_ID | Unique document key |
| Entity_ID | FK → Entity_Profile |
| ISO_Metric | FK → metric in ISO_Metric_Availability |
| Document_Type | HR report, LMS export, survey PDF, … |
| File_Name | Supporting file name |
| Source_System | Originating system |
| Last_Updated | Evidence date |
| Status | Validated / Partial / Missing |

**Relationship:** Links every metric to auditable files for ISO 30414 reviews.

---

## 4. Operational workbook (existing)

**File:** `data/Doha_Oasis_Sindibad_Database.xlsx`

Used for correlation analytics, HR/finance KPIs, and agent Q&A:

- `Correlation_Data`, `Monthly_HR`, `Finance`, `Employees`, …
- Department-level metrics (Hospitality, Retail, IT, …)

**Note:** SBU entities and Excel departments are complementary layers — SBU for ISO corporate readiness, Excel sheets for operational correlation intelligence.

---

## 5. API & code map

| Layer | Module |
|-------|--------|
| Load CSV + Excel | `app/data/loader.py` |
| SBU readiness math | `app/services/sbu_iso.py` |
| Dashboard KPIs | `app/services/dashboard.py` |
| Corporate SBU strip | `GET /api/v1/dashboard` → `sbu_corporate` |
| SBU questions | `try_sbu_iso_query()` via `POST /api/v1/advise` |

---

## 6. Example questions Sindibad can answer

- Which SBU has the largest ISO data gaps?
- Which metrics are missing in Printemps?
- Which departments need additional evidence?
- Show corporate SBU ISO 30414 readiness report
- What ISO metrics are available for Quest Theme Park?

---

## 7. Developer quick test

```bash
python -m pytest tests/test_agent.py -k sbu -q
curl http://localhost:8002/api/v1/dashboard | jq .sbu_corporate
```
