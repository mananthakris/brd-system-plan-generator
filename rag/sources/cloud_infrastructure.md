# Cloud Infrastructure — Verdant Intelligence

## Cloud Strategy

**Primary cloud:** AWS (us-east-1 primary, us-west-2 DR)
**Secondary cloud:** GCP us-central1 — ML workloads only (SageMaker alternative; under evaluation for consolidation)
**Multi-cloud principle:** Avoid where possible. GCP presence is legacy; roadmap item to consolidate to AWS SageMaker by 2026.

## AWS Account Structure

| Account | Purpose |
|---|---|
| verdant-prod | Production workloads |
| verdant-staging | Staging environment (mirrors prod topology) |
| verdant-dev | Development; developers have broader IAM permissions |
| verdant-security | Security tooling, GuardDuty aggregation, CloudTrail |

## Compute

| Service | Usage |
|---|---|
| ECS Fargate | API service (FastAPI), Celery workers, Airflow workers |
| Lambda | Utility webhook consumers, S3 event processors, scheduled data sync jobs |
| EC2 (minimal) | Bastion host only (us-east-1a); all application workloads are container/serverless |

**Networking:**
- VPC with public/private subnets in 3 AZs
- Application Load Balancer → ECS Fargate (API)
- NAT Gateway for outbound Lambda/Fargate calls
- VPC Endpoints for S3 and DynamoDB (cost optimisation)

## Data

| Service | Usage | Scale |
|---|---|---|
| RDS Aurora PostgreSQL | Transactional DB | r6g.large; ~800GB, ~2k QPS peak |
| Snowflake | Analytics warehouse | Enterprise, 2 virtual warehouses (COMPUTE_WH, REPORTING_WH) |
| S3 | Raw meter data, reports, ML training data | ~4TB; lifecycle rules to Glacier after 2 years |
| ElastiCache Redis | API cache + Celery broker | cache.r7g.large; single-AZ (acceptable for cache) |
| SQS FIFO | Utility webhook ingestion | verdant-meter-ingest.fifo |
| DynamoDB | Feature flags, ephemeral session data | On-demand pricing |

## Networking & Security

| Aspect | Configuration |
|---|---|
| WAF | AWS WAF on ALB; rules for OWASP top 10 |
| DDoS | AWS Shield Standard |
| Secrets | AWS Secrets Manager; rotated every 90 days |
| Encryption at rest | All S3, RDS, Snowflake encrypted (AES-256) |
| Encryption in transit | TLS 1.2+ enforced everywhere |
| IAM | Least-privilege; task roles for ECS; no long-lived keys in applications |
| SOC 2 Type II | Certified (2024); annual renewal |

## Observability

| Tool | Use |
|---|---|
| Datadog APM | Distributed tracing across FastAPI → Celery → Lambda |
| Datadog Logs | Centralised log aggregation; 30-day retention |
| Datadog Dashboards | SLA dashboards for report generation SLO (99.5% success, <60s p95) |
| PagerDuty | On-call alerts; escalation policies for P1/P2 |
| AWS CloudTrail | Audit log; forwarded to security account |
| AWS Config | Compliance rules for SOC 2 controls |

## Cost Profile (monthly, approximate)

| Category | Monthly cost |
|---|---|
| Compute (ECS + Lambda) | ~$3,200 |
| Data (RDS + ElastiCache + SQS) | ~$2,800 |
| Snowflake | ~$4,500 |
| S3 + data transfer | ~$800 |
| Monitoring (Datadog) | ~$2,100 |
| Other (WAF, secrets, misc) | ~$600 |
| **Total AWS + Snowflake** | **~$14,000** |

## Deployment Process

- GitHub Actions → Docker build → ECR push → ECS rolling deployment
- Blue/green deployments for API (zero-downtime)
- Lambda deployed via SAM CLI in GitHub Actions
- Terraform state in S3 + DynamoDB locking
- Promotion path: dev → staging (automated on merge to main) → prod (manual approval gate)

## Capacity Limits & Known Constraints

- Aurora PostgreSQL: approaching read IOPS limit on compliance report generation days (month-end); read replica planned for Q3 2025.
- SQS FIFO throughput: capped at 300 msg/s per queue; sufficient for current meter count (~12k active meters), will need sharding at ~50k meters.
- Snowflake COMPUTE_WH: occasionally queued on first-of-month report runs; upgrading from XS to S warehouse is approved but not yet applied.
- Lambda concurrency: soft limit 1000 in us-east-1; current peak ~180; headroom acceptable for next 18 months.
