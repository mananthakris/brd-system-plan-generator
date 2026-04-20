# Business Requirements Document
## Automated Carbon Penalty Forecasting Engine
**Author:** Priya Nair (VP Engineering) + Sasha Kim (Head of Product)
**Version:** 1.2
**Date:** 2025-03-10
**Status:** Approved for Engineering Planning

---

## 1. Objective

Build an automated carbon penalty forecasting engine that calculates projected fines for buildings subject to NYC Local Law 97 based on current and historical energy consumption data. The engine must provide 12-month rolling forecasts, support what-if scenario modelling (e.g., "what if we retrofit the HVAC system?"), and surface results in both the Verdant platform UI and via API for third-party integrations.

This is the highest-priority product initiative for Q2–Q3 2025. LL97 Phase 1 compliance period began 2024; the first penalty assessment notices from NYC DEP are expected in late 2025. Customers need actionable forecasts now.

---

## 2. Background

Verdant currently shows historical carbon intensity and a static "current year vs. limit" comparison. Customers must manually project whether they will exceed their annual carbon limit. This is error-prone, time-consuming for large portfolios, and a support burden.

Three enterprise customers ($2.1M ARR combined) have threatened churn if forecasting is not available by Q3 2025. A fourth is conditional on this feature before signing a $400k contract.

---

## 3. Functional Requirements

### 3.1 Forecast Calculation
- FR-01: Calculate projected annual carbon emissions for each NYC building based on the trailing 12 months of meter data, adjusted for seasonal patterns.
- FR-02: Compare projected emissions to the building's LL97 annual carbon limit (derived from occupancy type + gross floor area).
- FR-03: Calculate projected penalty in USD = max(0, (projected_emissions - carbon_limit) × $268).
- FR-04: Update forecasts automatically when new meter data arrives (within 30 minutes of ingestion).
- FR-05: Support buildings with multiple fuel types (electricity, natural gas, steam, fuel oil #2, fuel oil #4).

### 3.2 Scenario Modelling
- FR-06: Allow users to define up to 5 reduction scenarios per building (e.g., "reduce electricity by 15%", "replace natural gas with heat pump").
- FR-07: Each scenario must recalculate projected emissions and penalty delta vs. baseline.
- FR-08: Scenarios are user-saved and persist across sessions.

### 3.3 Portfolio View
- FR-09: Display portfolio-level penalty exposure (sum across all NYC buildings).
- FR-10: Rank buildings by penalty risk (highest exposure first).
- FR-11: Filter by compliance status: on-track | at-risk | over-limit.

### 3.4 API & Export
- FR-12: Expose forecast data via existing REST API (new endpoints); authenticated via existing Cognito tokens.
- FR-13: Include forecast data in the existing LL97 compliance PDF report.
- FR-14: Webhook notification when a building transitions from on-track → at-risk (configurable threshold, default 90% of limit).

---

## 4. Non-Functional Requirements

- NFR-01: Forecast recalculation must complete within 30 minutes of new meter data arriving for portfolios up to 500 buildings.
- NFR-02: API response time for forecast read endpoints: p95 < 500ms.
- NFR-03: Forecast data freshness displayed to the user (timestamp of last recalculation).
- NFR-04: Calculation accuracy: projected annual emissions must be within ±5% of actual for buildings with ≥10 months of complete data (validated quarterly against closed compliance years).
- NFR-05: All forecast data subject to existing tenant isolation controls (RLS, Snowflake view scoping).
- NFR-06: System must handle buildings with data gaps (< 12 months of data) with explicit uncertainty flagging.

---

## 5. Constraints

- CONST-01: Must use existing carbon factor tables (updated annually by NYC DEP); no external carbon calculation API.
- CONST-02: Forecasting logic must be auditable — every calculation step must be loggable and reproducible from stored inputs.
- CONST-03: Must not require changes to the Green Button Connect ingestion pipeline (treat as read-only data source).
- CONST-04: New API endpoints must be backward-compatible with existing API versioning scheme (v1/).
- CONST-05: No new cloud providers; must deploy on existing AWS infrastructure.
- CONST-06: Feature must be behind a feature flag for phased rollout to customer segments.

---

## 6. Stakeholders

| Role | Name | Involvement |
|---|---|---|
| Executive Sponsor | CEO (David Chen) | Final approval on scope trade-offs |
| Product Owner | Sasha Kim (Head of Product) | Requirements, acceptance criteria |
| Engineering Lead | Marco Delgado (Staff Eng) | Architecture, technical decisions |
| Data Lead | Yuki Tanaka (Data Eng) | dbt models, Snowflake queries |
| Customer Success | Lena Park | Validating with at-risk customers |
| QA | (contractor, TBD) | Testing forecasting accuracy |

---

## 7. Success Criteria

- SC-01: 3 enterprise customers confirm the forecasting feature meets their needs in UAT before GA release.
- SC-02: Forecast accuracy (NFR-04) validated on at least 2 closed compliance buildings before GA.
- SC-03: API response time SLO (NFR-02) met in load testing at 2× expected peak traffic.
- SC-04: Zero data leakage incidents in penetration test (scoped to new forecast endpoints).
- SC-05: Churn risk of 3 named enterprise customers eliminated (confirmed by Customer Success).

---

## 8. Timeline

| Milestone | Target date |
|---|---|
| Engineering plan approved | 2025-04-01 |
| Architecture design review | 2025-04-15 |
| Backend implementation complete | 2025-06-15 |
| Frontend implementation complete | 2025-06-30 |
| Internal QA + accuracy validation | 2025-07-15 |
| Customer UAT (3 accounts) | 2025-07-31 |
| GA release (feature flag lift) | 2025-08-15 |

---

## 9. Budget

- Engineering time: 2 senior backend engineers + 1 data engineer + 0.5 frontend engineer for 16 weeks.
- Infrastructure: Minimal incremental cost expected; forecast recalculation jobs will use existing Celery workers and Snowflake COMPUTE_WH.
- External services: No new paid services.

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Meter data gaps for key customers | High | Medium | Build explicit uncertainty model; flag incomplete data |
| NYC DEP updates carbon factors mid-year | Medium | High | Version carbon factor tables; support retroactive recalculation |
| Snowflake cost spike from forecast recalculation queries | Medium | Medium | Query optimisation + materialised intermediate results |
| QA contractor availability | Medium | Low | Identify backup contractor by April |
| Frontend team capacity (dashboard redesign overlap) | High | Medium | Scope frontend to read-only views first; interactive scenario modelling in v1.1 |

---

## 11. Out of Scope

- Forecasting for non-NYC regulations (Chicago BEPO, Boston BERDO) — v2 roadmap.
- ML-based forecasting models — current release uses deterministic calculation with seasonal adjustment; ML upgrade is post-GA.
- Real-time (sub-minute) forecast updates — 30-minute cadence is sufficient per ADR-006.
- Mobile app — web only.
- Automated penalty payment or regulatory submission.
