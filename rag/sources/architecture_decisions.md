# Architecture Decision Records — Verdant Intelligence

## ADR-001: Event-driven ingestion via SQS + Lambda (2022-03)

**Status:** Accepted

**Context:** Utility meter data arrives via webhook pushes from Green Button Connect partners (ComEd, ConEd, PG&E). Early architecture polled REST APIs hourly, causing rate-limit errors and stale data windows of up to 90 minutes.

**Decision:** Replace polling with an event-driven pipeline. Each utility webhook POST enqueues a message to an SQS FIFO queue. Lambda consumers process in order, deduplicate by meter_id + interval_start, and write to S3 raw bucket before transforming.

**Consequences:**
- Latency from meter read to database dropped from ~90 min to ~4 min average.
- Lambda cold starts acceptable at current volume (<2000 meters per customer).
- At >50k meters per tenant, SQS+Lambda will need replacement with Kinesis Data Streams.

**Tags:** data-ingestion, serverless, utility-api

---

## ADR-002: Snowflake as analytical warehouse; PostgreSQL for transactional data (2022-06)

**Status:** Accepted

**Context:** Compliance reporting requires aggregating 15-minute interval data across thousands of meters over multi-year windows. PostgreSQL struggled with query times exceeding 30 seconds for large portfolio reports.

**Decision:** Dual-database strategy:
- PostgreSQL (RDS Aurora): transactional data — accounts, buildings, meter configs, user settings, audit logs.
- Snowflake: all time-series energy data, benchmarking aggregates, compliance calculation results.

**Data flow:** Lambda → S3 (raw) → dbt (transform) → Snowflake (served). dbt runs on Airflow DAGs on a 15-min cadence.

**Consequences:**
- Report query times reduced from 30s → sub-2s for 95th percentile.
- Introduced dual-write complexity for building metadata (mirrored to Snowflake via CDC).
- Snowflake cost scales with query volume; added query tagging to identify expensive report types.

**Tags:** data-warehouse, analytics, snowflake, dbt

---

## ADR-003: Reject GraphQL; maintain REST + OpenAPI (2023-01)

**Status:** Accepted

**Context:** Frontend team proposed GraphQL to reduce over-fetching in the portfolio dashboard. Compliance export endpoints return deeply nested objects causing N+1 patterns.

**Decision:** Rejected GraphQL due to:
1. Team has no GraphQL production experience; learning curve for 2-person backend team deemed too high.
2. Existing REST clients (property management system integrations) can't be migrated without breaking changes.
3. Problem is better solved with response shaping (sparse fieldsets) and smarter pagination.

**Alternative implemented:** Added `?fields=` query param support to top 5 most-called endpoints. Reduced payload sizes by 60–70% on dashboard calls.

**Tags:** api-design, rest, graphql-rejected

---

## ADR-004: Adopt dbt for all Snowflake transformations (2022-08)

**Status:** Accepted

**Context:** Initial transforms were bespoke Python scripts run in Lambda, with no lineage tracking, inconsistent naming, and duplicated business logic for EUI (Energy Use Intensity) calculations.

**Decision:** Migrate all transforms to dbt models. Staging models mirror raw S3 ingestion. Intermediate models compute EUI, carbon factors, and compliance thresholds. Mart models serve the API and BI layer.

**Consequences:**
- Full lineage graph in dbt docs.
- EUI calculation logic lives in one place — `int_building_eui.sql`.
- dbt tests catch schema drift within one Airflow cycle.
- Adds ~15-min latency to data freshness vs. direct Lambda writes (acceptable for compliance use case).

**Tags:** dbt, data-transformation, analytics-engineering

---

## ADR-005: Multi-tenant data isolation via row-level security (2023-06)

**Status:** Accepted

**Context:** SOC 2 Type II audit required demonstrating that tenant A cannot access tenant B data. Prior approach relied solely on application-layer filtering, which auditors flagged as insufficient.

**Decision:** Implement row-level security (RLS) in PostgreSQL using tenant_id column on all sensitive tables. Snowflake uses virtual private data sharing — each customer gets a dedicated Snowflake view scoped to their org_id.

**Consequences:**
- Application queries must always include tenant context; missing tenant context throws a 403, not a data leak.
- Performance overhead ~5% on write-heavy tables; acceptable.
- Snowflake sharing adds ~$200/month per enterprise customer; priced into enterprise tier.

**Tags:** security, multi-tenancy, rls, soc2

---

## ADR-006: Reject real-time streaming for compliance calculations (2024-01)

**Status:** Accepted

**Context:** Product team requested live carbon penalty forecasts updating as new meter data arrives. Proposed implementation used Flink or Spark Streaming.

**Decision:** Rejected real-time streaming for compliance calculations. Regulatory compliance periods are monthly/annual — sub-minute latency has no customer value. Streaming infrastructure would double infrastructure complexity and cost for a feature customers haven't explicitly requested.

**Decision:** Near-real-time (15-min cadence via dbt + Airflow) is sufficient. Re-evaluate if customers with >10 buildings request live dashboards in a paid tier.

**Tags:** streaming-rejected, compliance-calculations, cost-optimisation
