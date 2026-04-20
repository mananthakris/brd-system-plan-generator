# Current Tools & Technology Stack — Verdant Intelligence

## Backend

| Layer | Technology | Version / Notes |
|---|---|---|
| Primary language | Python | 3.12 |
| Web framework | FastAPI | 0.111 — async, OpenAPI auto-docs |
| Task queue | Celery | Redis broker; used for report generation jobs |
| ORM | SQLAlchemy | 2.0, async sessions |
| Migrations | Alembic | All schema changes through migration files |
| Auth | AWS Cognito | JWT tokens; custom RBAC middleware |

## Frontend

| Layer | Technology | Notes |
|---|---|---|
| Framework | React | 18, TypeScript |
| State | Zustand | Replaced Redux in 2023 |
| Charts | Recharts | Energy use timeline charts |
| Design system | Tailwind CSS + shadcn/ui | |
| Build | Vite | |

## Data & Analytics

| Layer | Technology | Notes |
|---|---|---|
| Transactional DB | PostgreSQL | Aurora Serverless v2 (AWS) |
| Analytical warehouse | Snowflake | Enterprise; 2 virtual warehouses |
| Transformation | dbt | Core; ~140 models |
| Orchestration | Apache Airflow | MWAA (managed on AWS) |
| Cache | Redis | ElastiCache; API response cache + Celery |
| Object storage | S3 | Raw meter data, report PDFs, exports |

## ML / AI (nascent)

| Tool | Use case |
|---|---|
| scikit-learn | Baseline anomaly detection in meter readings |
| SageMaker | One model in production: EUI outlier detection |
| OpenAI API | Pilot — natural language compliance Q&A (internal only) |

## Infrastructure & DevOps

| Tool | Use |
|---|---|
| Cloud | AWS primary; GCP us-central1 for ML workloads (SageMaker alternative) |
| IaC | Terraform (modules for VPC, RDS, ECS, S3, SQS) |
| Containers | Docker; ECS Fargate for API and workers |
| CI/CD | GitHub Actions — lint, test, deploy to ECS |
| Secrets | AWS Secrets Manager |
| Monitoring | Datadog (APM, logs, dashboards); PagerDuty on-call |
| Error tracking | Sentry |

## Communication & Planning

| Tool | Use |
|---|---|
| Code hosting | GitHub (github.com/verdant-intelligence) |
| Issue tracking | Linear |
| Docs | Notion |
| Communication | Slack |
| Incident management | PagerDuty + Datadog monitors |

## Third-party Integrations (active)

| Partner | Integration type | Data |
|---|---|---|
| Green Button Connect | REST + webhook | Utility interval meter data |
| ENERGY STAR Portfolio Manager | REST API | Benchmarking scores, certifications |
| Measurabl | CSV import | Sustainability reporting data |
| Yardi | REST (beta) | Building metadata, lease data |
| MRI Software | REST (beta) | Property management sync |
| Buildium | Webhook (planned Q3 2025) | Multifamily property data |

## Regulatory / Compliance Data Sources

| Source | Format | Cadence |
|---|---|---|
| NYC Local Law 97 carbon limits table | Static JSON (versioned) | Updated annually by NYC DEP |
| Chicago BEPO thresholds | Static CSV | Updated annually |
| Boston BERDO targets | Static JSON | Updated annually |
| CBECS national benchmarks | Static CSV | Updated every 4 years (EIA) |
| EPA emissions factors | Static JSON | Updated annually |
