# Engineering Team Skills — Verdant Intelligence

## Team Composition (as of 2025-Q1)

Total engineering: 12 people
- 1 VP Engineering (Priya Nair) — system design, hiring, no IC work
- 1 Staff Engineer (Marco Delgado) — architecture, cross-team, Python/AWS expert
- 3 Senior Backend Engineers — Python, FastAPI, PostgreSQL, AWS
- 2 Mid-level Backend Engineers — Python, FastAPI; growing into infrastructure
- 2 Senior Frontend Engineers — React, TypeScript, data visualisation
- 1 Data Engineer — dbt, Airflow, Snowflake, Python
- 1 ML Engineer — Python, scikit-learn, SageMaker; building out ML capability
- 1 DevOps/Platform Engineer — Terraform, AWS, Docker, GitHub Actions

## Skill Depth by Technology

### Strong (production-proven, multiple team members)
- Python (FastAPI, SQLAlchemy, Celery, async)
- PostgreSQL (query optimisation, RLS, schema design)
- AWS (ECS Fargate, RDS, S3, SQS, Lambda, Cognito, Secrets Manager)
- dbt + Airflow (data pipeline patterns)
- React + TypeScript
- Docker + GitHub Actions CI/CD

### Medium (1–2 people, some production use)
- Snowflake (data engineer + staff eng; SQL proficient, Snowpark not used)
- Terraform (DevOps eng primarily; others can read/modify)
- Redis (used in production, not deeply tuned)
- scikit-learn (ML eng; SageMaker deployment experience)
- LLM APIs / prompt engineering (OpenAI API pilot; 2 engineers involved)

### Developing (learning, no production use yet)
- LangChain / LangGraph (no production use; staff eng ran a spike)
- Kafka / Kinesis (evaluated, not adopted; ADR-006)
- Kubernetes (team uses ECS Fargate; K8s migration on 2026 roadmap)
- Spark / PySpark (ML eng has academic exposure)
- GraphQL (evaluated, rejected in ADR-003)

### Gaps (no meaningful experience)
- Go, Rust, Java (no team members with production experience)
- GCP beyond BigQuery basics
- Real-time streaming systems in production
- Mobile (iOS/Android)

## Team Norms & Constraints

- **Sprint cadence:** 2-week sprints; 80% of capacity allocated to product work
- **On-call rotation:** 4-person rotation (backend + DevOps); 1 week per 4 weeks
- **Hiring velocity:** 1–2 hires per quarter; competitive market, climate tech premium
- **Code review:** All PRs require 1 approval; senior engineer for architecture-affecting changes
- **Testing standard:** Unit tests required; integration tests for data pipelines; E2E tests for critical user flows (report generation, compliance export)
- **Documentation:** ADRs for architecture decisions; Notion for runbooks; OpenAPI for API contracts

## Capacity Planning Notes

- Staff engineer (Marco) is the primary reviewer for system design proposals.
- ML engineer is at 80% capacity on the EUI outlier model; available for new ML work in Q3 2025.
- Data engineer is the sole dbt/Airflow owner — bus factor risk acknowledged; cross-training mid-backend engineer in progress.
- Frontend team is fully allocated through Q2 2025 on the dashboard redesign.
- New hire (senior backend) expected to start 2025-05-01.
