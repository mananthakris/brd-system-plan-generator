# Compliance Standards — Arbor Risk (Lending)

## FCRA — Fair Credit Reporting Act (15 U.S.C. § 1681)

### Adverse Action Reason Codes
- When Arbor's fraud score contributes to an adverse action on a consumer credit application, the lender must issue an adverse action notice to the applicant
- Arbor must supply up to **4 reason codes** per decision that explain the principal factors driving the score
- Reason codes must be: human-readable, non-jargon, non-discriminatory, and map to documented model features
- Reason codes must be **stable identifiers** — if a reason code is in use, its `code_id` and consumer-facing text may not change without a compliance review
- Example reason codes Arbor provides:
  - "Insufficient length of credit history"
  - "Number of recent applications for credit"
  - "Identity information could not be fully verified"
  - "Inconsistency between stated and verified income information"

### Permissible Purpose
- Arbor may only pull bureau data for a **permissible purpose** under FCRA Section 604 — the applicant must have applied for credit with the lender and the lender must have a signed authorisation
- Arbor must not pull bureau data speculatively or for internal model training without a permissible purpose record
- Bureau pull records (who was pulled, when, for which lender) retained for 5 years

### Model Documentation
- All consumer-facing models must have a current **model card** documenting: feature list, training data period, known limitations, fairness analysis results
- Model cards updated at each model promotion event

---

## ECOA / Regulation B

- Prohibits discrimination in credit decisions based on race, colour, religion, national origin, sex, marital status, age, or income from public assistance
- **Arbor's models must not use features that serve as proxies for protected characteristics**
- Prohibited proxies include: ZIP code used in isolation (race proxy), first name or surname patterns (ethnicity/gender proxy), language of application interaction
- **Annual disparate impact analysis required** on all consumer-facing models
- Equalized odds and demographic parity metrics reported to Arbor's Compliance team quarterly
- All findings and remediation steps documented in model card

---

## GLBA — Gramm-Leach-Bliley Act

- Applicant data received from lenders is **non-public personal information (NPI)** under GLBA
- Arbor may only use NPI for the fraud scoring purpose for which it was shared — not for cross-lender profiling, marketing, or other secondary uses without consent
- Arbor must maintain a written information security programme (WISP) covering NPI
- NPI must be encrypted at rest and in transit; access controls enforce minimum necessary access
- Data retention: NPI retained only as long as needed for fraud scoring and model training (maximum 5 years); deleted on request within GLBA guidelines

---

## BSA / AML — Bank Secrecy Act

- When Arbor's fraud signals indicate patterns consistent with money laundering (e.g. synthetic identity ring funnelling loan proceeds, bust-out coordinated at scale), Arbor must support the lender's SAR filing obligation
- Arbor's CaseTrack must provide a SAR workflow: flag case for AML review, draft SAR narrative from case data, support e-filing via FinCEN BSA E-Filing System
- Arbor retains SAR-related records for 5 years per BSA requirement

---

## GDPR / CCPA

### Right to Deletion
- Consumer deletion requests must be fulfilled within **30 days** (GDPR) or **45 days** (CCPA, extendable to 90)
- Deletion must cascade across: Aurora PostgreSQL, DynamoDB, Snowflake, S3 data lake, Redis (TTL handles ephemeral data), MLflow experiment artefacts that contain personal data
- **Exception**: bureau pull records and fraud investigation records may be retained for the legally required period for fraud prevention (GDPR Article 17(3)(d)) before hard deletion

### Data Minimisation
- Arbor collects only the personal data necessary for fraud detection — no additional data fields collected speculatively
- All data fields documented in the data catalogue with purpose, legal basis, and retention period
- EU applicant data must not be processed outside EU/EEA without Standard Contractual Clauses (SCCs) in place

### Data Subject Rights
- Right to know: Arbor must enumerate all data held about a consumer on request
- Right to object to automated decision-making: Arbor must provide a human review path for any applicant who disputes an automated fraud decision
- DSR pipeline (Airflow) orchestrates enumeration and deletion across all data stores

---

## SOC 2 Type II

- Arbor holds SOC 2 Type II certification (Trust Service Criteria: Security, Availability, Confidentiality)
- Annual audit window; evidence collection automated via Drata
- All production changes require a change management record (Jira ticket + approval + Drata evidence link)
- Access reviews: quarterly for production systems; annual for all other access
- Penetration testing: annual external pentest of production environment
