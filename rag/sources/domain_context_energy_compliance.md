# Domain Context: Energy Benchmarking & Building Compliance

## Key Regulations Verdant Supports

### NYC Local Law 97 (LL97)
- Enacted 2019 as part of the Climate Mobilization Act.
- Applies to buildings >25,000 sq ft in NYC.
- Sets annual carbon intensity limits (kg CO2e / sq ft) per occupancy type.
- Buildings exceeding limits face fines of $268 per metric ton CO2e over the limit.
- Compliance periods: 2024–2029 (Phase 1), 2030–2034 (Phase 2, stricter limits).
- Data requirement: Annual energy consumption by fuel type, converted to carbon using NYC-specific emissions factors.
- Verdant workflow: Ingest utility data → calculate building carbon intensity → compare to LL97 limit table → forecast penalty → generate LL97 compliance report (PDF).

### NYC Local Law 84 (LL84) — Benchmarking
- Annual energy and water benchmarking submission to NYC via ENERGY STAR Portfolio Manager.
- Required for buildings >25,000 sq ft (same threshold as LL97).
- Deadline: May 1 each year for prior calendar year data.
- Verdant workflow: Pull interval data → aggregate to monthly totals → submit via Portfolio Manager API → archive submission receipt.

### Chicago Building Energy Performance Standard (BEPO)
- Applies to buildings >50,000 sq ft.
- Requires meeting an Energy Use Intensity (EUI) target by 2024, 2027, 2030.
- Targets set by property type (office, multifamily, retail, etc.).
- Penalty: $0.10/sq ft/year for non-compliant buildings.

### Boston Building Emissions Reduction and Disclosure Ordinance (BERDO 2.0)
- Applies to buildings >20,000 sq ft.
- Sets emissions intensity targets declining through 2050.
- Annual reporting required.

### CA AB 802
- Statewide benchmarking for commercial buildings >50,000 sq ft.
- Annual disclosure to CEC; no direct penalty but public disclosure creates market pressure.

## Key Metrics

| Metric | Definition |
|---|---|
| EUI (Energy Use Intensity) | kBtu / sq ft / year; primary benchmarking metric |
| Carbon Intensity | kg CO2e / sq ft / year; used for LL97 compliance |
| GHG Emissions | Total metric tons CO2e; sum across all fuel types |
| ENERGY STAR Score | 1–100 percentile vs. similar buildings nationally |
| Penalty Forecast | $ estimated fine if current trajectory continues to compliance deadline |

## Data Model Concepts

- **Building:** Physical structure with address, gross floor area (GFA), occupancy type, year built.
- **Meter:** Utility meter associated with a building; has fuel type (electricity, natural gas, steam, fuel oil).
- **Interval Reading:** Timestamped consumption value from a meter (15-min or hourly granularity).
- **Compliance Period:** Date range for a regulation (e.g., LL97 2024–2029).
- **Benchmark Submission:** Annual data package submitted to a regulatory body.
- **Carbon Factor:** Emissions conversion rate; varies by fuel type, utility, and year (NYC factors change annually).

## Customer Segments

| Segment | Building types | Key pain points |
|---|---|---|
| REIT / Institutional | Mixed commercial portfolios | LL97 penalty exposure across 100s of buildings; board-level ESG reporting |
| Multifamily Operators | Residential apartment buildings | LL97 applies; utility data access hard (tenant-paid utilities) |
| Property Managers (3rd party) | Manage on behalf of owners | Need multi-client view; white-labelling requests |
| Sustainability Consultants | Advisory clients | Need export/audit trail for client deliverables |
| Municipalities | Public buildings | Annual benchmarking for public disclosure; budget-constrained |

## Common Technical Challenges

- **Utility data gaps:** Green Button Connect coverage is ~70% of US utilities; remainder requires manual CSV upload or screen-scraping.
- **Tenant-paid utilities:** In multifamily and commercial leases, tenants pay utilities directly; landlords can't access interval data without tenant consent or whole-building metering.
- **Data quality:** Meter malfunctions, estimated reads, and timezone mismatches cause calculation errors; anomaly detection is critical.
- **Emissions factor updates:** NYC updates carbon factors annually; retroactive recalculation required for prior-year reports.
- **Square footage discrepancies:** Self-reported GFA in Portfolio Manager often differs from tax records; affects EUI calculations.
