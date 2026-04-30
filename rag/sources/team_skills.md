# Team Skills — Arbor Risk Engineering (Lending Fraud)

## Team Composition (as of 2025-Q2)

### ML Engineering — 10 engineers

**Strengths:**
- Python 3.12 (expert), scikit-learn, XGBoost, LightGBM (expert)
- Feature engineering for tabular identity and bureau data (expert) — tradeline aggregates, velocity windows, identity consistency features
- SageMaker training pipelines and MLflow experiment tracking — proficient
- Model explainability: SHAP TreeExplainer (expert — core to FCRA compliance); LIME (familiar)
- Fairness analysis tools (Aequitas, custom disparate impact scripts) — proficient
- Snowflake + dbt for feature pipeline ownership — proficient

**Gaps:**
- Graph neural networks — 2 engineers exploring for synthetic identity ring detection; not yet production-ready
- Real-time streaming feature computation — not needed for current async scoring model; low priority
- NLP / LLM fine-tuning — out of scope for fraud models

---

### Backend Engineering — 7 engineers

**Strengths:**
- Python FastAPI (expert), async Python, pydantic v2
- AWS Step Functions — proficient; owns the scoring workflow state machine
- SQS consumer/producer patterns — proficient
- Aurora PostgreSQL (expert) — complex query optimisation, case management schema, migration tooling
- Redis (proficient) — bureau response cache, TTL patterns, Lua scripting for atomic operations
- DynamoDB (familiar) — scoring result store, single-table design for job tracking
- External API integration — Experian, Equifax, TransUnion, LexisNexis (proficient in handling retries, auth, rate limits)

**Gaps:**
- Go / high-performance gateway — not needed for lending latency targets; no Go in the stack
- Kafka / event streaming — not used; SQS/SNS covers async patterns
- Graph database operations (Neo4j, Neptune) — not in production; 1 engineer exploring

---

### Data Engineering — 3 engineers

**Strengths:**
- Snowflake + dbt (expert) — all feature models, training data pipelines, lender reporting
- Apache Spark on EMR (expert) — large-scale feature backfills, model training dataset preparation
- Airflow / MWAA (expert) — nightly feature pipeline, batch scoring DAGs, DSR workflows
- Great Expectations — proficient; pipeline data quality gates
- Evidently AI — proficient; model drift reports

---

### Platform Engineering — 2 engineers

**Strengths:**
- Kubernetes / EKS (expert), Terraform (expert), ArgoCD (proficient)
- Datadog (expert) — dashboards, SLO tracking, Step Functions metrics
- AWS services broadly — proficient; strong in EKS, SQS, Aurora, ElastiCache, DynamoDB, S3, Step Functions

**Gaps:**
- GCP / Azure — no experience; AWS-only shop

---

### Security — 1 engineer

- GLBA WISP maintenance, AWS IAM least-privilege, VPC security
- Snyk code scanning + Amazon Inspector container scanning
- Splunk SIEM administration
- FCRA / GLBA compliance controls ownership
- Annual penetration testing coordination

---

## Hiring Constraints

- No headcount approvals for new roles until Q4 2025
- All new features must be buildable with current team composition
- No mobile SDK development capability in-house

## Technology Preferences

1. AWS-native managed services strongly preferred
2. Python for all services — no Go, no Java
3. Avoid introducing new database technologies unless existing stores are clearly a poor fit
4. New external API integrations require security review and GLBA data use assessment
5. No real-time streaming infrastructure (Kafka, Kinesis) — SQS/SNS covers all async needs at current scale
