# BRD — FCRA Adverse Action Reason Code Engine (ReasonIQ v1)

**Document owner**: Head of Compliance  
**Status**: Approved for engineering planning  
**Priority**: P0 — Q2 2025 (regulatory deadline)

---

## 1. Problem Statement

Under FCRA, when Arbor's fraud score contributes to an adverse action on a consumer credit application, the lender must issue an adverse action notice with up to 4 human-readable reason codes explaining the principal factors driving the score. Arbor is currently responsible for supplying these reason codes to lenders via the ScoreIQ API response.

The current system generates reason codes by ranking raw SHAP feature importances and mapping them to a small static code table (12 codes). This approach has two critical gaps:

1. **Coverage gaps**: 7% of scored applications return fewer than 4 reason codes because the current code table does not cover all feature combinations surfaced by the model
2. **Code stability violation**: reason code text was modified in a February 2025 deployment without a compliance review, potentially violating the FCRA requirement that `code_id` and consumer-facing text be stable identifiers

Compliance has flagged both issues. A new reason code engine is required to be in production before Q3 2025.

---

## 2. Goals

1. Ensure 100% of adverse-action-eligible decisions return exactly 4 reason codes
2. Expand the reason code catalogue from 12 to ≥ 40 codes covering all model feature groups
3. Enforce code stability: `code_id` and consumer text locked after compliance sign-off; changes require a formal review record
4. Support reason code versioning: a scored application retains the reason codes active at time of scoring (audit trail for disputes)
5. Decouple reason code catalogue management from model deployments

---

## 3. Scope

**In scope**:
- Reason code catalogue: schema, storage, versioning, and management API
- SHAP-to-reason-code mapping logic (feature group → code lookup with fallback rules)
- Reason code audit trail: each scored application record retains `reason_code_version` and the 4 codes at time of scoring
- Compliance review workflow: draft codes surface in a staging environment; compliance officer approves before promotion
- Reason code catalogue admin UI (lightweight — internal compliance team use only)
- Migration of existing 12 codes into the new catalogue schema with versioning backfill

**Out of scope**:
- Consumer-facing adverse action letter generation (lender's responsibility)
- Adverse action notice delivery channel (lender responsibility)
- Changes to the underlying ML models

---

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | Reason code catalogue MUST store: `code_id` (stable), `short_text` (consumer-facing), `feature_group`, `model_version_scope`, `status` (draft / active / retired), `compliance_approved_at` |
| FR-02 | SHAP output MUST map to reason codes via feature group; top 4 non-overlapping feature groups MUST always resolve to 4 codes |
| FR-03 | If fewer than 4 feature groups have SHAP values above threshold, system MUST select from a ranked fallback list of generic codes |
| FR-04 | `code_id` and `short_text` for active codes MUST be immutable after compliance approval; any change MUST create a new `code_id` |
| FR-05 | Each scoring result MUST record `reason_code_version` (catalogue snapshot hash) alongside the 4 reason codes returned |
| FR-06 | Compliance admin MUST be able to: create draft codes, promote to active, retire codes, and view full change history |
| FR-07 | Reason codes MUST be returned in the ScoreIQ API response under `reason_codes: [{code_id, short_text}]` |
| FR-08 | Reason code text MUST be human-readable, non-jargon, and non-discriminatory (FCRA § 615) |

---

## 5. Non-Functional Requirements

| Category | Target |
|---|---|
| Coverage | 100% of adverse-action-eligible decisions return exactly 4 reason codes |
| Latency contribution | < 5ms additional p99 latency to ScoreIQ pipeline |
| Audit retention | Reason code records retained for 5 years per FCRA |
| Compliance | FCRA § 615 adverse action · ECOA non-discrimination · SOC 2 change management |

---

## 6. Constraints

- Reason code catalogue stored in Aurora PostgreSQL (no new database technology)
- No real-time SHAP recomputation — SHAP values computed as part of the scoring worker, passed to reason code engine
- Catalogue admin UI must use existing Auth0 SSO for compliance officer access
- All catalogue changes (promote, retire) require a Jira change management record for SOC 2 audit

---

## 7. Stakeholders

| Role | Name | Interest |
|---|---|---|
| Compliance | FCRA/GLBA Lead | Code accuracy, stability, audit trail |
| ML Engineering | Lead ML Engineer | SHAP-to-code mapping quality |
| Backend Engineering | Lead Backend Engineer | API integration, catalogue service design |
| Product | Head of Product, Lending | Coverage guarantee (100% at 4 codes) |
| Legal | General Counsel | FCRA liability, code stability |
