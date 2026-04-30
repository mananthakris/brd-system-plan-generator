# BRD — First-Party Fraud Case Management (CaseTrack v2)

**Document owner**: Head of Product, Lending  
**Status**: Approved for engineering planning  
**Priority**: P1 — Q3 2025

---

## 1. Problem Statement

When ScoreIQ flags an application as high-risk or a portfolio re-scoring job crosses a risk threshold, a fraud case is created and assigned to an analyst in CaseTrack. The current CaseTrack v1 system has three critical limitations:

1. **No SAR workflow**: Cases involving money laundering patterns (synthetic identity rings, bust-out fraud coordinated at scale) require the lender to file a Suspicious Activity Report (SAR) with FinCEN. CaseTrack v1 has no SAR narrative drafting or e-filing support — analysts export case data manually and file outside the system, creating a BSA/AML compliance gap.
2. **No outcome feedback loop**: Case dispositions (confirmed fraud, false positive, analyst override) are not written back to the training data pipeline. The ML team cannot use analyst-confirmed fraud labels for model retraining without a manual data extract.
3. **Slow case queue performance**: The case queue query (all open cases, sortable by risk tier, assignee, lender) executes a full-table scan on Aurora and times out at > 5,000 open cases, which occurs during peak origination periods.

---

## 2. Goals

1. Implement a SAR workflow: flag case for AML review, generate SAR narrative draft from case data, support FinCEN BSA E-Filing System submission
2. Close the outcome feedback loop: confirmed fraud / false positive dispositions written to Aurora and synced to Snowflake for model retraining
3. Fix case queue performance to p99 < 500ms for up to 50,000 open cases
4. Support bulk case actions (bulk assign, bulk close, bulk export) for analyst efficiency

---

## 3. Scope

**In scope**:
- SAR workflow: AML review flag, SAR narrative draft (templated from case data), FinCEN BSA E-Filing integration
- Case disposition recording: confirmed_fraud, false_positive, inconclusive, escalated_to_lender
- Outcome sync to Snowflake: nightly Airflow DAG writes confirmed fraud labels to `arbor_labels.analyst_outcomes`
- Case queue performance fix: covering index on Aurora + query optimisation; read replica routing for all list queries
- Bulk case actions: assign, close, export (CSV) for up to 500 cases per action
- BSA record retention: SAR-related case data retained for 5 years

**Out of scope**:
- Automated SAR filing decision (analyst always makes the filing decision — no auto-SAR)
- Integration with lender's own case management system
- Consumer-facing dispute portal
- Mobile interface

---

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | Analyst MUST be able to flag a case as requiring AML review from the case detail view |
| FR-02 | System MUST generate a SAR narrative draft from case data: applicant identity fields, fraud signals, timeline of events, amounts at risk |
| FR-03 | SAR submission MUST support FinCEN BSA E-Filing System API (analyst reviews draft, confirms, submits) |
| FR-04 | SAR record MUST be retained for 5 years; case record MUST not be deletable while SAR is pending or filed |
| FR-05 | Analyst MUST be able to record case disposition: `confirmed_fraud`, `false_positive`, `inconclusive`, `escalated_to_lender` |
| FR-06 | Confirmed fraud dispositions MUST be written to `arbor_labels.analyst_outcomes` in Snowflake within 24 hours |
| FR-07 | Case queue list endpoint MUST return p99 < 500ms for up to 50,000 open cases |
| FR-08 | Bulk actions (assign, close, export) MUST support up to 500 cases per request |
| FR-09 | All case actions MUST be logged to the audit trail with analyst identity, timestamp, and action type |
| FR-10 | GLBA access controls: bureau pull data in case view accessible only to users with `fraud_analyst` or `fraud_supervisor` role |

---

## 5. Non-Functional Requirements

| Category | Target |
|---|---|
| Case queue p99 latency | < 500ms at 50,000 open cases |
| Case detail p99 latency | < 300ms |
| SAR narrative generation | < 5 seconds (acceptable — analyst reviews before submission) |
| Availability | 99.9% monthly |
| Retention | SAR records: 5 years · Case records: 5 years |
| Compliance | BSA/AML SAR workflow · GLBA NPI access controls · SOC 2 audit trail · FCRA 5-year bureau record retention |

---

## 6. Constraints

- SAR narrative must be reviewed and confirmed by a human analyst before submission — no auto-filing
- FinCEN BSA E-Filing API integration requires security review and legal sign-off
- Aurora PostgreSQL is the authoritative case store — no migration to another database
- All case data exports must be encrypted at rest and require analyst authentication
- GLBA: bureau pull data visible only to `fraud_analyst` / `fraud_supervisor` IAM roles

---

## 7. Stakeholders

| Role | Name | Interest |
|---|---|---|
| Product | Head of Product, Lending | Analyst efficiency, case throughput |
| Compliance | BSA/AML Officer | SAR workflow compliance, FinCEN integration |
| Backend Engineering | Lead Backend Engineer | Query performance, SAR API integration |
| Data Engineering | Lead Data Engineer | Outcome feedback loop to Snowflake |
| Lender Success | Enterprise CSM | Lender visibility into case outcomes |
| Legal | General Counsel | BSA liability, SAR record retention |
