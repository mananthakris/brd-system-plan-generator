# Current Tools & Technology Stack — Arbor Risk (Lending Fraud)

## Cloud & Infrastructure

| Layer | Technology | Notes |
|---|---|---|
| Cloud provider | AWS | Primary: us-east-1 · DR: us-west-2 |
| Container orchestration | EKS (Kubernetes 1.30) | Graviton nodes (m7g) for API services |
| Workflow orchestration (scoring) | AWS Step Functions | Multi-step scoring pipeline per application |
| CI/CD | GitHub Actions + ArgoCD | GitOps; all deploys via ArgoCD sync |
| Infrastructure as code | Terraform | All infrastructure defined as Terraform modules |
| Secrets | AWS Secrets Manager | API keys for bureau providers and lender webhooks |

## Data & Async Processing

| Layer | Technology | Notes |
|---|---|---|
| Async job queue | Amazon SQS | Application scoring jobs queued and consumed by worker pool |
| Event streaming | Amazon SNS | Webhook fan-out to lender endpoints; scoring completion events |
| Feature computation | Snowflake + dbt | Nightly pre-computed feature snapshots (no real-time feature store) |
| Data warehouse | Snowflake | Primary analytics, model training data, lender reporting |
| Data transformation | dbt | Runs against Snowflake; all feature models version-controlled |
| Batch compute | Apache Spark on EMR | Large-scale feature backfills and model training datasets |
| Workflow orchestration (batch) | Apache Airflow (MWAA) | Nightly feature pipeline, SageMaker batch scoring, DSR workflows |

## Databases

| Store | Technology | Use case |
|---|---|---|
| Relational | Aurora PostgreSQL 15 | Applications, fraud cases, analyst data, audit trail |
| Key-value / cache | ElastiCache Redis 7.0 | Bureau API response cache (24h TTL), scoring job state |
| Document / high-throughput | DynamoDB | Completed scoring job results (polling endpoint, 7-day TTL) |

## Machine Learning

| Layer | Technology | Notes |
|---|---|---|
| Model training | SageMaker | XGBoost, LightGBM for application fraud and synthetic identity |
| Experiment tracking | MLflow (on EKS) | All experiments tracked |
| Model registry | SageMaker Model Registry | Champion/challenger gating before promotion |
| Inference (real-time) | FastAPI on EKS | Application scoring worker; models loaded in-memory |
| Inference (batch) | SageMaker Batch Transform | Nightly portfolio re-scoring on Spot instances |
| Feature store | Snowflake feature snapshot table | Pre-computed nightly; no Tecton (latency target does not require it) |
| Model monitoring | Evidently AI | PSI, data drift on monthly holdout |
| Data quality | Great Expectations | Pre-training pipeline validation |

## Application Layer

| Layer | Technology | Notes |
|---|---|---|
| Primary language | Python 3.12 | All services — ML, API, workers, data pipelines |
| API framework | FastAPI | Scoring API, CaseTrack API, internal services |
| Explainability | SHAP (TreeExplainer) | Reason code generation for XGBoost/LightGBM models |
| Task queue | Celery + Redis | Background jobs (report generation, bulk export) |
| Auth | Auth0 (external) + JWT (internal) | Lender-facing SSO + service-to-service tokens |

## External Integrations

| Integration | Purpose | Notes |
|---|---|---|
| Experian API | Bureau pull (primary) | Tri-merge, dual, or single pull depending on risk tier |
| Equifax API | Bureau pull (secondary) | Used in dual and tri-merge tiers |
| TransUnion API | Bureau pull (tertiary) | Used in tri-merge tier only |
| LexisNexis Accurint | Identity verification | Address history, phone/SSN association |
| Email reputation API | Email domain age + risk | Third-party API; 24h response cache in Redis |

## Observability

| Layer | Technology | Notes |
|---|---|---|
| Metrics + APM | Datadog | Agents on all EKS nodes + Step Functions metrics |
| Log aggregation | Datadog + S3 | Hot: Datadog · Cold: S3 Glacier |
| Distributed tracing | Datadog APM | OpenTelemetry; traces scoring pipeline end-to-end |
| Alerting | PagerDuty | P1/P2 routing to on-call |
| Compliance audit | Drata | SOC 2 evidence automation |
| ML observability | LangSmith | AI pipeline tracing (used by internal AI tooling) |
