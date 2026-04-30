# Domain Context — Lending Fraud Detection

## What Arbor Risk Does

Arbor Risk is a lending fraud detection platform. We build in-house ML models that help lending platforms — personal loan originators, BNPL providers, auto lenders, and mortgage platforms — detect first-party fraud and synthetic identity at the application and funding stages before money leaves the door.

We do not operate in card authorization or payment processing. Our scoring is asynchronous (seconds, not milliseconds) and sits upstream of the lender's underwriting decision.

## Customer Profile

| Segment | Description |
|---|---|
| Personal loan originators | Online lenders (fintech and bank) offering unsecured personal loans $1k–$50k |
| BNPL providers | Buy-now-pay-later platforms with high application volume and thin identity signals |
| Auto lenders | Dealer-facing and direct-to-consumer auto financing; longer loan lifecycle |
| Mortgage platforms | Digital mortgage originators; lower volume, higher value, stronger bureau data |

## The Fraud Problem We Solve

### First-Party Fraud
The applicant is a real person who deliberately misrepresents income, employment, or intent to repay. They receive funds and default without attempting to repay. This is the most common fraud type in consumer lending and is structurally hard to detect because the identity is genuine.

Key signals: income inflation patterns, employment tenure mismatch, device and email age, application velocity (same person applying across multiple lenders), bureau tradeline behaviour.

### Synthetic Identity Fraud
The applicant is a fabricated identity — a combination of a real SSN (often belonging to a child, deceased person, or inactive credit user) with a false name, date of birth, and address. The attacker slowly builds a credit history ("credit piggybacking") then busts out by maxing credit lines.

Key signals: SSN-to-name/DOB mismatch at bureau, thin file with recent sudden activity, address shared across many identities, phone/email not associated with the SSN holder's history, no prior relationship with the lender.

## Application Lifecycle (Arbor's Position)

1. Applicant submits loan application on lender's platform
2. Lender calls Arbor's ScoreIQ API with the application payload (no raw SSN/PAN sent — tokenised)
3. Arbor pulls bureau data (Experian, Equifax, TransUnion) using the applicant's identity tokens
4. Arbor computes features (bureau tradelines, device signals, velocity, identity consistency) and runs ML model
5. Arbor returns a fraud risk score (0–1000), a risk tier (low/medium/high/decline), and up to 4 FCRA reason codes
6. Lender's underwriting system uses the fraud score as one input into the credit decision
7. If declined, the lender issues an adverse action notice using Arbor's reason codes (FCRA requirement)
8. Confirmed fraud outcomes (default, SAR filing, investigation result) returned to Arbor as ground truth labels (T+60 to T+180 days)

## Scoring Targets

| Metric | Target |
|---|---|
| Scoring API p99 latency | < 3 seconds (async enrichment path) |
| Scoring API p50 latency | < 1.5 seconds |
| Model AUC on monthly holdout | > 0.88 (first-party) · > 0.91 (synthetic identity) |
| False positive rate | < 1.5% of legitimate applications declined |
| Availability | 99.9% (< 8.7 hours downtime/year) |
| Bureau API timeout fallback | Degrade to rules-only score, flag as unverified |

## Regulatory Environment

| Regulation | Key Constraint |
|---|---|
| FCRA (15 U.S.C. § 1681) | Adverse action on consumer credit must include up to 4 reason codes |
| ECOA / Reg B | Model features must not use protected class proxies; annual disparate impact analysis |
| GLBA | Applicant data received from lenders is non-public personal information (NPI); strict use limitation |
| BSA / AML | SAR filing required when fraud indicators suggest money laundering |
| GDPR / CCPA | Right to deletion; applicant data subject to data minimisation and residency rules |
| SOC 2 Type II | Annual audit; all production changes require change management record |

## Arbor Product Lines

| Product | Description |
|---|---|
| ScoreIQ | Asynchronous application fraud scoring API — returns score, risk tier, reason codes |
| IdentityGraph | Synthetic identity detection — cross-references bureau, device, phone, and email signals |
| ReasonIQ | FCRA-compliant adverse action reason code engine — SHAP-based, human-readable |
| CaseTrack | Analyst workbench — investigation workflow, ground truth labelling, SAR drafting |

## Key Operational Metrics Arbor Tracks

- **Application fraud rate** by lender, loan type, and channel
- **Model precision at 5% decline rate** (primary business metric for lender customers)
- **Reason code distribution** — weekly review for ECOA compliance (no protected class concentration)
- **Bureau pull cost** — Experian/Equifax/TransUnion charge per pull; Arbor optimises with caching and tiered pull strategy
- **Label return rate** — % of scored applications that return a confirmed outcome within 180 days
