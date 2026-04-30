# Fraud Pattern Library — Arbor Risk (Lending)

## First-Party Fraud Patterns

### Income and Employment Misrepresentation
- Applicant inflates stated income or fabricates employer to qualify for a larger loan
- Signals: stated income significantly above bureau-inferred income band, employer phone number resolves to a VoIP or non-business number, employment start date too recent to match claimed tenure, payroll direct deposit history absent from bank account data
- Model features: income_stated_vs_bureau_ratio, employer_phone_type, employment_tenure_months, bank_account_payroll_deposit_flag

### Bust-Out Intent (First-Party)
- Applicant opens credit with intent to max out and default without repayment
- Signals: rapid application velocity across multiple lenders in a short window (only detectable via consortium data), no payment on first statement, account opened with high utilisation immediately, prior address linked to other bust-out accounts
- Model features: applications_last_30d_consortium, days_to_first_missed_payment (lagged label), address_bust_out_flag

### Straw Buyer / Loan Stacking
- Applicant applies simultaneously at multiple lenders using the same identity to obtain more credit than any single lender would approve
- Signals: inquiry burst on bureau (3+ hard inquiries in 7 days from different lenders), same application submitted with minor variations (different phone number or email), device fingerprint seen applying at competitor lenders (consortium signal)
- Model features: hard_inquiry_count_7d, hard_inquiry_count_30d, inquiry_lender_diversity

### Intentional Default (BNPL)
- BNPL applicant disputes delivery to avoid repayment; or obtains goods and immediately resells
- Signals: high dispute rate on prior BNPL accounts, shipping address is a freight forwarder or reshipping service, goods category (electronics, gift cards) combined with new account, email domain age < 30 days

---

## Synthetic Identity Fraud Patterns

### Classic Synthetic Identity (Credit Piggybacking)
- Attacker combines a real SSN (often belonging to a child, elderly person, or deceased individual with an inactive credit file) with a fabricated name and date of birth
- Builds credit over 12–24 months by being added as an authorised user on legitimate accounts ("piggybacking"), then applies for credit and busts out
- Signals: SSN-to-name mismatch at bureau, SSN issued date inconsistent with stated DOB (e.g. SSN from 1970s but DOB is 1995), file age < 24 months with sudden inquiry burst, address not associated with the SSN holder in any prior record

### Fully Fabricated Identity
- Attacker generates a non-existent SSN (tests against bureau — no file found means the SSN is clean and can be cultivated)
- Less common due to SSN validation at origination, but occurs with test SSNs and errors in bureau matching
- Signals: no bureau file found for SSN + DOB combination, SSN fails Experian SSN validation check, SSN area number inconsistent with state of birth/residence

### Identity Manipulation
- Existing real person with credit history has their identity details modified slightly (address, phone, DOB digit change) to obscure derogatory marks or prior fraud flags
- Signals: slight DOB mismatch across applications (1 year off), phone number not associated with identity in LexisNexis, address change to a forwarding address in the 30 days before application

---

## Detection Feature Reference

### Identity Consistency Features
| Feature | Source | Signal Direction |
|---|---|---|
| ssn_name_match_score | Experian/Equifax | Low score = synthetic risk |
| ssn_dob_consistency | Bureau SSN validation | Mismatch = high risk |
| ssn_issue_year_vs_dob | Bureau | Issued before DOB = synthetic flag |
| address_ssn_association_years | LexisNexis | < 1 year = elevated risk |
| phone_identity_match | Telco lookup | Not associated = elevated risk |
| email_domain_age_days | Email reputation API | < 90 days = elevated risk |

### Velocity and Application Behaviour Features
| Feature | Source | Signal Direction |
|---|---|---|
| hard_inquiries_7d | Bureau | > 3 = high risk |
| hard_inquiries_30d | Bureau | > 5 = very high risk |
| applications_same_device_30d | Internal device store | > 2 = high risk |
| lenders_applied_30d_consortium | Consortium | > 3 = loan stacking risk |
| days_since_oldest_tradeline | Bureau | < 12 months = thin file risk |

### Bureau File Health Features
| Feature | Source | Signal Direction |
|---|---|---|
| tradeline_count | Bureau | 0–1 = thin file |
| derogatory_mark_count | Bureau | > 0 = prior default risk |
| utilisation_rate | Bureau | > 90% = stress signal |
| authorised_user_tradeline_ratio | Bureau | > 0.8 = piggybacking flag |
| file_age_months | Bureau | < 24 with burst = synthetic risk |

---

## Fraud Ring Patterns

### Synthetic Identity Ring
- Coordinated group creates dozens of synthetic identities, cultivates them in parallel, then busts out simultaneously
- Signals: cluster of applications sharing an address, phone prefix, or email domain; device fingerprints overlapping across identities; bureau inquiries showing same lenders in same time window
- Detection: graph clustering on shared identity attributes; requires cross-application linkage in internal store

### Referral Ring (First-Party)
- Recruiter pays individuals to apply for loans they intend to default on; recruiter takes a cut of funded amounts
- Signals: IP address shared across multiple applicants, same device fingerprint submitting multiple applications, social network overlap in contact data

---

## Bureau Pull Strategy

Arbor uses a tiered pull strategy to balance fraud signal quality against per-pull cost:

| Tier | Trigger | Bureaus Pulled |
|---|---|---|
| Full tri-merge | Application score > 400 (high risk) | Experian + Equifax + TransUnion |
| Dual pull | Application score 200–400 (medium risk) | Experian + one secondary |
| Single pull | Application score < 200 (low risk) | Experian only |
| No pull | Rules-only decline (hard decline before ML) | None |

Cache policy: bureau responses cached in Redis for 24 hours per identity token. Same applicant reapplying within 24 hours reuses the cached response to avoid double-billing.
