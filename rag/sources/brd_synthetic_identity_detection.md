# BRD — Synthetic Identity Detection Pipeline (IdentityGraph v1)

**Document owner**: Head of ML, Lending  
**Status**: Approved for engineering planning  
**Priority**: P1 — Q3 2025

---

## 1. Problem Statement

Synthetic identity fraud (fabricated or manipulated SSN/DOB/name combinations) represents 35% of Arbor's lending fraud losses by dollar value. The current application fraud model (XGBoost, trained on bureau tradelines) has a 41% detection rate for confirmed synthetic identities at a 1% false positive rate — significantly below the 70% target set by the Compliance and Product teams. Synthetic identities are difficult for the current model because they often have thin but legitimate-looking credit files built through credit piggybacking, which score well on traditional tradeline features.

---

## 2. Goals

1. Increase synthetic identity detection rate from 41% to ≥ 70% at 1% FPR
2. Detect credit piggybacking patterns at the time of application (not post-origination)
3. Surface consortium-level signals: same SSN/address/phone used across multiple lenders' applications
4. Produce an `identity_risk_tier` (`LOW` / `MEDIUM` / `HIGH`) as an input feature to the application fraud score
5. Ensure all model features are ECOA-compliant (no protected characteristic proxies)

---

## 3. Scope

**In scope**:
- Feature engineering for synthetic identity signals: credit file age vs. applicant stated age, tradeline velocity, authorised user account patterns, identity field consistency (SSN-DOB-name cross-bureau match), address history anomalies
- Cross-lender consortium velocity features (via Arbor's internal consortium — no PII sharing, hashed tokens only)
- New LightGBM synthetic identity model trained on 24-month labelled dataset
- Integration of `identity_risk_tier` output into existing ScoreIQ scoring pipeline (passed as an input feature)
- SHAP-based reason codes for synthetic identity model (mapped to FCRA reason code catalogue)
- Fairness analysis: demographic parity and equalized odds across age, gender, race proxies

**Out of scope**:
- Graph neural network approach (2 engineers exploring — not production-ready for Q3)
- Real-time consortium syndication (async nightly batch only)
- Device biometrics or behavioural signals

---

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | Pipeline MUST compute synthetic identity features from bureau pull data during the scoring workflow |
| FR-02 | Model MUST produce an `identity_risk_tier` (`LOW` / `MEDIUM` / `HIGH`) and a continuous `synthetic_identity_score` (0–1) |
| FR-03 | Reason codes for synthetic identity decisions MUST be drawn from the approved FCRA catalogue |
| FR-04 | Consortium velocity features MUST use hashed applicant tokens — raw PII MUST NOT leave Arbor's VPC |
| FR-05 | Model MUST pass ECOA fairness analysis (disparate impact ratio ≥ 0.80 across protected groups) |
| FR-06 | Model card MUST be completed and signed off by Compliance before promotion to production |
| FR-07 | Synthetic identity score MUST be passed as an input feature to the application fraud model at inference time |
| FR-08 | All features MUST be pre-computable as part of the nightly Snowflake dbt pipeline |

---

## 5. Non-Functional Requirements

| Category | Target |
|---|---|
| Detection rate | ≥ 70% at 1% FPR on holdout set |
| Inference latency contribution | < 50ms additional latency to ScoreIQ p99 |
| Training data period | 24 months labelled applications |
| Fairness threshold | Disparate impact ≥ 0.80 (Aequitas) |
| Compliance | FCRA reason codes · ECOA fairness · GLBA NPI · model card required |

---

## 6. Constraints

- Training data must have a documented permissible purpose under FCRA
- No real-time feature computation — features computed nightly in Snowflake
- Model must be explainable via SHAP TreeExplainer (GNNs ruled out for this release)
- Consortium velocity features require security review and GLBA data use assessment before implementation
- No headcount additions — must be built by current 10 ML engineers + 7 backend engineers

---

## 7. Stakeholders

| Role | Name | Interest |
|---|---|---|
| ML Engineering | Lead ML Engineer | Feature engineering, model quality |
| Compliance | FCRA/GLBA Lead | Reason codes, fairness, permissible purpose |
| Data Engineering | Lead Data Engineer | Snowflake dbt feature pipeline |
| Product | Head of Product, Lending | Detection rate vs. false positive balance |
| Lender Success | Enterprise CSM | Explaining synthetic identity flags to lender analysts |
