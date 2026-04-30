# BRD — Application Fraud Scoring Service (ScoreIQ v2)

**Document owner**: Head of Product, Lending  
**Status**: Approved for engineering planning  
**Priority**: P0 — Q3 2025

---

## 1. Problem Statement

Lending partners submitting consumer credit applications require a fraud score and FCRA-compliant reason codes within 3 seconds of submission. The current scoring service is a monolithic FastAPI app that executes bureau pulls, feature lookups, and ML inference synchronously. Under load (> 200 concurrent applications), p99 latency exceeds 8 seconds and timeouts cause application abandonment on the lender side. Additionally, the service has no retry logic for bureau API failures, resulting in approximately 2.3% of applications returning incomplete scores.

---

## 2. Goals

1. Achieve p99 end-to-end scoring latency < 3 seconds for 95% of applications
2. Reduce incomplete score rate from 2.3% to < 0.5% via robust retry and fallback logic
3. Support tiered bureau pull strategy (tri-merge / dual / single) to reduce bureau API costs
4. Deliver up to 4 FCRA-compliant adverse action reason codes per scored application
5. Scale to 500 concurrent applications without manual intervention

---

## 3. Scope

**In scope**:
- Asynchronous application submission and scoring pipeline
- Integration with Experian, Equifax, TransUnion bureau APIs
- Integration with LexisNexis Accurint for identity verification
- ML inference using current XGBoost application fraud model (v4.2)
- SHAP-based reason code generation (top 4 features)
- Webhook delivery and polling endpoint for lender result retrieval
- Bureau API response caching (24h TTL per applicant identity token)

**Out of scope**:
- Portfolio re-scoring (separate SageMaker batch job — ADR-007)
- Synthetic identity detection model (separate BRD)
- Lender-facing dashboard or reporting

---

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | System MUST accept application payload via `POST /v1/score` and return a `job_id` within 200ms |
| FR-02 | Scoring worker MUST execute bureau pulls in parallel where the tier requires multiple bureaus |
| FR-03 | System MUST retry failed bureau API calls up to 3 times with 500ms exponential backoff |
| FR-04 | On bureau API unavailability, system MUST fall back to rules-only score with `bureau_available: false` flag |
| FR-05 | ML inference MUST complete within 200ms p99 |
| FR-06 | Completed score MUST be delivered to lender webhook within 3 seconds p99 of job submission |
| FR-07 | Score result MUST be queryable via `GET /v1/score/{job_id}` polling endpoint |
| FR-08 | Each decision MUST include up to 4 reason codes drawn from the approved FCRA reason code catalogue |
| FR-09 | Bureau API responses MUST be cached per applicant identity token with 24h TTL |
| FR-10 | All NPI in transit MUST use TLS 1.3; at rest MUST use AES-256 via KMS |

---

## 5. Non-Functional Requirements

| Category | Target |
|---|---|
| End-to-end p99 latency | < 3 seconds |
| Job submission p99 latency | < 200ms |
| Availability | 99.9% monthly (< 44 min downtime) |
| Throughput | 500 concurrent scoring jobs |
| Bureau API error tolerance | < 0.5% incomplete score rate |
| Compliance | FCRA adverse action reason codes · GLBA NPI handling · SOC 2 audit trail |

---

## 6. Constraints

- AWS-only infrastructure (no GCP or Azure)
- Python 3.12 for all services (no Go, no Java)
- No real-time streaming infrastructure (SQS/SNS only)
- No Tecton or online feature store — Snowflake feature snapshots only
- Bureau API credentials stored in AWS Secrets Manager; not logged
- All production changes require SOC 2 change management record

---

## 7. Stakeholders

| Role | Name | Interest |
|---|---|---|
| Product | Head of Product, Lending | Feature delivery, lender SLAs |
| ML Engineering | Lead ML Engineer | Model serving, reason code quality |
| Backend Engineering | Lead Backend Engineer | Pipeline reliability, bureau integration |
| Compliance | FCRA/GLBA Compliance Lead | Reason code accuracy, NPI handling |
| Lender Success | Enterprise CSM | Lender onboarding and SLA reporting |
