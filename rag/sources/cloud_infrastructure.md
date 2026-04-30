# Cloud Infrastructure — Arbor Risk (Lending Fraud)

## Regions & Availability

- **Primary region**: us-east-1 (3 AZs active)
- **DR region**: us-west-2 (warm standby — RPO 15 min, RTO 60 min)
- All stateful services deployed Multi-AZ within primary region

## Network Topology

| Segment | Details |
|---|---|
| VPC CIDR | 10.0.0.0/8 split into environment-specific VPCs |
| Environments | production, staging, dev — separate VPCs connected via Transit Gateway |
| Egress | NAT Gateway per AZ |
| AWS service access | PrivateLink for Aurora, ElastiCache, DynamoDB, SQS |
| External API connectivity | Outbound HTTPS to Experian, Equifax, TransUnion, LexisNexis via NAT Gateway with egress IP allowlisting at bureau side |

## Compute

| Tier | Technology | Notes |
|---|---|---|
| API and scoring workers | EKS node groups — m7g.xlarge Graviton | Python FastAPI services; right-sized for CPU-bound ML inference |
| Batch scoring | SageMaker Batch Transform on Spot | Nightly portfolio re-scoring; up to 70% cost saving on Spot |
| Batch pipelines | EMR on Spot | Spark feature backfills and model training |
| Lightweight orchestration | AWS Step Functions | Per-application scoring workflow; no persistent compute |

## Data Storage

| Service | Configuration | Retention |
|---|---|---|
| S3 | Raw application data, model artefacts, Spark output — Intelligent Tiering | 30d hot, 1yr warm, 5yr Glacier |
| EBS | Encrypted gp3 for EKS stateful sets | Snapshotted daily |
| Aurora PostgreSQL | Multi-AZ writer + 2 read replicas | Daily snapshots to S3, 90-day retention |
| ElastiCache Redis | Cluster mode — 2 primaries, 2 replicas | Bureau cache: 24h TTL · Job state: 1h TTL |
| DynamoDB | On-Demand capacity | Scoring results: 7-day TTL |

## Latency Targets (Production SLA)

| Path | Target | Measurement |
|---|---|---|
| Scoring API (job submission) | p99 < 200ms | Datadog APM |
| End-to-end scoring (submission to webhook) | p99 < 3 seconds | Step Functions execution duration |
| Bureau API pull (single bureau) | p99 < 1.5 seconds | Datadog external check |
| ML inference (in-memory model) | p99 < 200ms | Measured inside scoring pod |
| Polling endpoint (job result read) | p99 < 50ms | DynamoDB + Datadog |
| CaseTrack UI queries | p99 < 500ms | Aurora read replica + Datadog |

## Autoscaling

- **Scoring worker pods**: EKS HPA on SQS queue depth (KEDA SQS scaler — 1 pod per 50 queued jobs)
- **API pods**: EKS HPA on CPU utilisation (target 70%)
- **SageMaker Batch Transform**: scales automatically per job configuration
- **DynamoDB**: On-Demand — no pre-provisioning needed

## Security Boundaries

- All applicant NPI encrypted at rest (AES-256 via AWS KMS) and in transit (TLS 1.3)
- Bureau pull records stored in Aurora with restricted IAM access (scoring worker role only)
- GLBA NPI access logged to Datadog with service identity, timestamp, and purpose code
- Annual penetration testing of production environment
- All production changes require change management record (SOC 2 evidence via Drata)

## Disaster Recovery

- Aurora Global Database: cross-region replication lag < 1 second
- S3 Cross-Region Replication for all critical buckets (model artefacts, training data)
- EKS cluster in us-west-2 pre-configured; Route 53 health-check failover activates it
- Quarterly DR drill with RTO/RPO validation
