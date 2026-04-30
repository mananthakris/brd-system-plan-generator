# Architecture Decisions — Arbor Risk (Lending Fraud)

## ADR-001: Asynchronous Scoring via SQS + Worker Pool (2022-Q4)

**Decision**: Implement application fraud scoring as an asynchronous pipeline — application payload submitted to SQS, worker pool processes bureau pulls and ML inference, result delivered via webhook or polling endpoint.

**Context**: Lending fraud scoring is not on the authorization critical path (unlike card payments). Bureau API calls (Experian, Equifax, TransUnion) take 300ms–1.5s each and introduce variable latency. A synchronous API would either block for 2–4 seconds or timeout under load. Async pattern decouples submission from completion and allows retries on bureau timeouts without impacting the lender's application flow.

**Outcome**: Lender submits application via `POST /v1/score` and receives a `job_id` immediately. Worker picks up from SQS, pulls bureau data, runs ML model, writes result to DynamoDB, and calls lender's webhook. Lender can also poll `GET /v1/score/{job_id}`. p99 end-to-end < 3 seconds under normal bureau API conditions.

---

## ADR-002: Bureau API Response Caching in Redis (2023-Q1)

**Decision**: Cache bureau API responses in Redis for 24 hours per applicant identity token.

**Context**: Experian, Equifax, and TransUnion charge per pull. Same applicant reapplying within 24 hours (common in BNPL and personal loan shopping) would otherwise incur duplicate bureau costs. Bureau data does not meaningfully change within a 24-hour window for fraud scoring purposes.

**Outcome**: Redis key: `bureau:{bureau}:{identity_token}`. TTL: 24 hours. Cache hit rate ~18% across all pulls (higher for BNPL segment). Estimated annual saving: $240k in bureau costs. Cache invalidated on explicit request (e.g. after fraud investigation clears an identity).

---

## ADR-003: Snowflake + dbt for Feature Pre-computation (2023-Q2)

**Decision**: Pre-compute application fraud features in Snowflake using dbt models rather than a real-time feature store.

**Context**: Evaluated Tecton (real-time feature store) but the sub-10ms feature serving latency it provides is unnecessary for lending — our scoring target is 3 seconds. Tecton's operational overhead and licensing cost were not justified. Snowflake dbt models compute features nightly (bureau tradeline aggregates, address history, consortium velocity) and write to a feature snapshot table. At scoring time, the worker queries Snowflake directly for pre-computed features and combines with real-time bureau pull.

**Outcome**: Feature pipeline runs nightly in Airflow (MWAA). Features stored in `arbor_features.application_feature_snapshot` Snowflake table. Real-time features (device fingerprint, email age) still computed inline at scoring time. Eliminated Tecton dependency entirely.

---

## ADR-004: Aurora PostgreSQL for Applications and Cases (2023-Q3)

**Decision**: Aurora PostgreSQL (writer + 2 read replicas) for application records, fraud cases, and analyst case management data.

**Context**: Application data has relational structure (application → bureau pulls → model scores → case → analyst actions → outcome labels) requiring joins and ACID guarantees. DynamoDB was evaluated but relational query patterns (analyst search, case history, outcome analysis) made it a poor fit.

**Outcome**: Primary data store for all application lifecycle and case management data. Read replicas serve CaseTrack analyst UI and reporting queries. Schema enforces application–case–outcome relationships with foreign key constraints.

---

## ADR-005: DynamoDB for Scoring Job Results (2023-Q4)

**Decision**: DynamoDB for storing completed scoring job results accessed by the polling endpoint.

**Context**: Scoring results must be readable by the lender's polling endpoint within milliseconds of the worker completing. Aurora was considered but would add read replica contention. DynamoDB On-Demand provides sub-10ms reads at scale without competing with the application/case tables.

**Outcome**: Partition key: `job_id`. TTL: 7 days (lender fetches result within minutes; 7 days provides grace period). Item contains: score, risk_tier, reason_codes, bureau_pull_summary, model_version, processing_time_ms. Writes from scoring worker; reads from polling API.

---

## ADR-006: Tiered Bureau Pull Strategy (2024-Q1)

**Decision**: Implement a three-tier bureau pull strategy — tri-merge for high-risk applications, dual pull for medium-risk, single pull for low-risk — based on a fast rules-only pre-screen.

**Context**: Bureau pulls are the largest variable cost in scoring. Full tri-merge (all three bureaus) costs ~$2.50 per application; single pull costs ~$0.80. Running rules against device, email, and phone signals first allows us to segment applications by risk before pulling bureau data.

**Outcome**: Rules pre-screen runs in < 100ms (no external API calls). Score from rules assigns applications to a tier. Bureau pulls execute in parallel within the tier. Tri-merge reserved for applications with high-risk pre-screen signals (synthetic identity indicators, application velocity flags). Reduced average bureau cost per application from $2.20 to $1.35.

---

## ADR-007: SageMaker Batch Transform for Portfolio Scoring (2024-Q2)

**Decision**: Use SageMaker Batch Transform for nightly portfolio-level fraud re-scoring of open loan applications and funded accounts.

**Context**: Lenders need ongoing monitoring — a borrower who looked clean at origination may show new fraud signals (e.g. consortium flags from other lenders, new derogatory marks). Nightly batch re-scoring using SageMaker Batch Transform is cost-effective (Spot instances) and does not compete with real-time scoring infrastructure.

**Outcome**: Airflow DAG triggers nightly SageMaker Batch Transform job on all open accounts. Results written to Snowflake for lender reporting and to Aurora for CaseTrack alerting. Accounts crossing a configurable risk threshold trigger a CaseTrack alert to the assigned analyst.

---

## ADR-008: Step Functions for Multi-Step Verification Workflow (2024-Q3)

**Decision**: Use AWS Step Functions to orchestrate the multi-step application scoring workflow (rules pre-screen → bureau pull → feature computation → ML inference → decision → webhook delivery).

**Context**: The scoring pipeline has multiple steps with branching logic (bureau timeout → fallback to rules-only, tri-merge vs single pull decision, retry on failure). Implementing this as inline application code was brittle and hard to observe. Step Functions provides visual workflow execution history, built-in retry/backoff per step, and branch logic without custom orchestration code.

**Outcome**: Each scoring job runs as a Step Functions execution. Execution history available in AWS console for debugging. Step-level timeouts and retries configured independently (bureau pull: 3 retries with 500ms backoff; ML inference: 1 retry; webhook delivery: 5 retries with exponential backoff). Replaced ~400 lines of retry/orchestration Python with a state machine definition.
