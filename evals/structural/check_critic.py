"""Deterministic structural checks for critic output, plus calibration fixtures."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


_DIMENSION_KEYS = {"completeness", "feasibility", "specificity", "consistency", "scope_fit"}
_WEIGHTS = {"completeness": 0.25, "feasibility": 0.25, "specificity": 0.20,
            "consistency": 0.15, "scope_fit": 0.15}


def check_all_five_dimensions_present(output: dict) -> CheckResult:
    content = output.get("content") or {}
    missing = _DIMENSION_KEYS - set(content.keys())
    passed = len(missing) == 0
    return CheckResult("all_five_dimensions_present", passed, float(passed),
                       f"Missing dimensions: {missing or 'none'}")


def check_scores_in_range(output: dict) -> CheckResult:
    content = output.get("content") or {}
    bad = [k for k in _DIMENSION_KEYS
           if not (0.0 <= (content.get(k) or {}).get("score", -1) <= 1.0)]
    passed = len(bad) == 0
    return CheckResult("scores_in_range", passed, float(passed),
                       f"Dimensions with out-of-range scores: {bad or 'none'}")


def check_overall_matches_weighted_formula(output: dict) -> CheckResult:
    content = output.get("content") or {}
    overall = content.get("overall_score")
    if overall is None:
        return CheckResult("overall_matches_weighted_formula", False, 0.0, "overall_score missing")
    expected = sum(
        (content.get(k) or {}).get("score", 0) * w
        for k, w in _WEIGHTS.items()
    )
    diff = abs(overall - expected)
    passed = diff < 0.02
    return CheckResult("overall_matches_weighted_formula", passed, float(passed),
                       f"overall={overall:.3f}, expected={expected:.3f}, diff={diff:.3f}")


def check_passed_consistent_with_score(output: dict) -> CheckResult:
    content = output.get("content") or {}
    bad = []
    for k in _DIMENSION_KEYS:
        dim = content.get(k) or {}
        score = dim.get("score", 0)
        passed_flag = dim.get("passed", None)
        if passed_flag is not None and passed_flag != (score >= 0.60):
            bad.append(k)
    passed = len(bad) == 0
    return CheckResult("passed_consistent_with_score", passed, float(passed),
                       f"Inconsistent passed flags: {bad or 'none'}")


def check_revision_required_consistent(output: dict) -> CheckResult:
    content = output.get("content") or {}
    overall = content.get("overall_score", 1.0)
    any_below_half = any(
        (content.get(k) or {}).get("score", 1.0) < 0.50
        for k in _DIMENSION_KEYS
    )
    expected_revision = overall < 0.70 or any_below_half
    actual_revision = content.get("revision_required", False)
    passed = expected_revision == actual_revision
    return CheckResult("revision_required_consistent", passed, float(passed),
                       f"revision_required={actual_revision}, expected={expected_revision}")


def check_revision_notes_when_required(output: dict) -> CheckResult:
    content = output.get("content") or {}
    revision_required = content.get("revision_required", False)
    notes = content.get("revision_notes")
    if revision_required:
        passed = bool(notes and len(notes.strip()) > 0)
        evidence = "revision_notes present" if passed else "revision_required=True but notes missing"
    else:
        passed = True
        evidence = "revision not required, notes check skipped"
    return CheckResult("revision_notes_when_required", passed, float(passed), evidence)


def check_feedback_nonempty_per_dimension(output: dict) -> CheckResult:
    content = output.get("content") or {}
    bad = [k for k in _DIMENSION_KEYS
           if len((content.get(k) or {}).get("feedback", "")) <= 20]
    passed = len(bad) == 0
    return CheckResult("feedback_nonempty_per_dimension", passed, float(passed),
                       f"Dimensions with short feedback: {bad or 'none'}")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


# ---------------------------------------------------------------------------
# Calibration fixtures — 3 quality tiers for testing critic sensitivity
# ---------------------------------------------------------------------------

FIXTURE_HIGH_QUALITY = {
    "plan_output": {
        "agent_name": "plan_generator",
        "content": {
            "project_overview": "Build a real-time fraud scoring service using Aurora Postgres for event storage and Flink for stream processing. The system will integrate with Arbor's existing Kafka bus and expose a gRPC API consumed by the underwriting engine.",
            "phases": [
                {"phase_number": 1, "name": "Data Pipeline Foundation", "objectives": ["Stand up Kafka consumer for application events", "Deploy Aurora Postgres schema v1 with fraud_events table"], "deliverables": ["kafka-consumer service deployed to EKS", "Aurora schema migration PR merged"], "duration_weeks": 3, "dependencies": []},
                {"phase_number": 2, "name": "Scoring Engine", "objectives": ["Implement Flink scoring job with velocity and graph features", "Expose gRPC endpoint for synchronous lookups"], "deliverables": ["flink-scoring-job passing unit tests with >90% coverage", "gRPC proto file and server deployed to staging"], "duration_weeks": 4, "dependencies": ["Data Pipeline Foundation"]},
                {"phase_number": 3, "name": "Integration & Rollout", "objectives": ["Shadow-mode testing against production traffic", "Gradual rollout with feature flag in underwriting engine"], "deliverables": ["shadow-mode dashboard in Grafana", "feature flag merged and rollout plan approved"], "duration_weeks": 3, "dependencies": ["Scoring Engine"]},
            ],
            "key_milestones": ["Kafka consumer live in staging (week 3)", "First model score generated in shadow mode (week 7)", "Full production rollout (week 10)"],
            "total_phases": 3,
            "total_weeks_estimate": 10,
        },
        "raw_text": "High quality plan stub",
        "model_used": "gpt-5.4",
        "tokens_used": 500,
        "created_at": "2026-04-24T00:00:00",
    },
    "architect_output": {
        "agent_name": "solution_architect",
        "content": {
            "problem_type": "new_feature",
            "classification_rationale": "BRD introduces a net-new real-time fraud scoring capability not present in any existing Arbor service.",
            "options": [
                {"option_id": "A", "name": "Flink Stream Processing", "description": "Real-time scoring via Apache Flink consuming Kafka events.", "high_level_components": ["KafkaConsumer", "FlinkScoringJob", "AuroraPostgres", "gRPCServer"], "data_flow": "Kafka → Flink → Aurora → gRPC → Underwriting", "integration_points": ["Kafka topic: application-events", "gRPC: scoring.v1.ScoreApplication"], "constraints_addressed": ["real-time <200ms SLA", "AWS-only"], "trade_offs": "Higher operational complexity vs batch", "estimated_complexity": "high"},
                {"option_id": "B", "name": "Lambda + DynamoDB", "description": "Serverless scoring triggered by SQS with DynamoDB for low-latency reads.", "high_level_components": ["SQSConsumer", "LambdaScorer", "DynamoDB", "APIGateway"], "data_flow": "SQS → Lambda → DynamoDB → REST → Underwriting", "integration_points": ["SQS queue: fraud-scoring", "REST: /v1/score"], "constraints_addressed": ["serverless ops", "AWS-only"], "trade_offs": "Cold start latency risk for p99", "estimated_complexity": "medium"},
            ],
            "recommended_option_id": "A",
            "recommendation_rationale": "Flink aligns with Arbor's existing Kafka infrastructure and provides sub-100ms scoring required by the BRD.",
        },
        "raw_text": "High quality architect stub",
        "model_used": "gpt-5.4",
        "tokens_used": 600,
        "created_at": "2026-04-24T00:00:00",
    },
    "tech_stack_output": {
        "agent_name": "tech_stack_recommender",
        "content": {
            "options": [
                {"name": "Flink + Aurora + gRPC", "rationale": "Extends existing Kafka/Aurora stack; team has Flink experience from the payment pipeline.", "pros": ["No new infra", "Sub-50ms p99 latency proven in payment pipeline"], "cons": ["Flink cluster management overhead"], "estimated_effort": "2 engineers × 10 weeks"},
                {"name": "Spark Structured Streaming", "rationale": "Alternative if Flink cluster management is a constraint.", "pros": ["Team has Spark experience", "Easier debugging"], "cons": ["Higher latency (~500ms)", "Requires dedicated EMR cluster"], "estimated_effort": "2 engineers × 12 weeks"},
            ],
            "recommended": "Flink + Aurora + gRPC",
            "rationale": "Flink is already in production for the payment pipeline; team capability and infra already in place.",
        },
        "raw_text": "High quality tech stack stub",
        "model_used": "gpt-5.4-mini",
        "tokens_used": 300,
        "created_at": "2026-04-24T00:00:00",
    },
}

FIXTURE_MED_QUALITY = {
    "plan_output": {
        "agent_name": "plan_generator",
        "content": {
            "project_overview": "Build fraud scoring service.",
            "phases": [
                {"phase_number": 1, "name": "Backend Development", "objectives": ["Build the backend"], "deliverables": ["backend service"], "duration_weeks": 6, "dependencies": []},
                {"phase_number": 2, "name": "Integration", "objectives": ["Integrate with existing systems", "Test the integration"], "deliverables": ["integration complete"], "duration_weeks": 4, "dependencies": ["Backend Development"]},
                {"phase_number": 3, "name": "Deployment", "objectives": ["Deploy to production", "Monitor rollout"], "deliverables": ["service deployed"], "duration_weeks": 2, "dependencies": ["Integration"]},
            ],
            "key_milestones": ["Backend done (week 6)", "Integration done (week 10)", "Deployed (week 12)"],
            "total_phases": 3,
            "total_weeks_estimate": 12,
        },
        "raw_text": "Medium quality plan stub",
        "model_used": "gpt-5.4",
        "tokens_used": 400,
        "created_at": "2026-04-24T00:00:00",
    },
    "architect_output": FIXTURE_HIGH_QUALITY["architect_output"],
    "tech_stack_output": FIXTURE_HIGH_QUALITY["tech_stack_output"],
}

FIXTURE_LOW_QUALITY = {
    "plan_output": {
        "agent_name": "plan_generator",
        "content": {
            "project_overview": "Implement the feature.",
            "phases": [
                {"phase_number": 1, "name": "Do everything", "objectives": ["Build it"], "deliverables": [], "duration_weeks": 20, "dependencies": []},
            ],
            "key_milestones": ["Done"],
            "total_phases": 1,
            "total_weeks_estimate": 20,
        },
        "raw_text": "Low quality plan stub",
        "model_used": "gpt-5.4",
        "tokens_used": 100,
        "created_at": "2026-04-24T00:00:00",
    },
    "architect_output": {
        "agent_name": "solution_architect",
        "content": {
            "problem_type": "greenfield",
            "classification_rationale": "New.",
            "options": [
                {"option_id": "A", "name": "Option A", "description": "Do it.", "high_level_components": ["service"], "data_flow": "input → output", "integration_points": [], "constraints_addressed": [], "trade_offs": "none", "estimated_complexity": "medium"},
            ],
            "recommended_option_id": "Z",  # wrong — doesn't match any option
            "recommendation_rationale": "Best option.",
        },
        "raw_text": "Low quality architect stub",
        "model_used": "gpt-5.4",
        "tokens_used": 200,
        "created_at": "2026-04-24T00:00:00",
    },
    "tech_stack_output": {
        "agent_name": "tech_stack_recommender",
        "content": {
            "options": [
                {"name": "Stack A", "rationale": "Good.", "pros": ["fast"], "cons": ["slow"], "estimated_effort": "some time"},
            ],
            "recommended": "Stack A",
            "rationale": "It is good.",
        },
        "raw_text": "Low quality tech stub",
        "model_used": "gpt-5.4-mini",
        "tokens_used": 100,
        "created_at": "2026-04-24T00:00:00",
    },
}


def run_calibration_checks(critic_agent) -> list[CheckResult]:
    """Run critic against 3 fixture tiers and verify calibration."""
    results = []
    tiers = [
        ("high", FIXTURE_HIGH_QUALITY, lambda s, r: s >= 0.80),
        ("med", FIXTURE_MED_QUALITY, lambda s, r: 0.45 <= s <= 0.80),
        ("low", FIXTURE_LOW_QUALITY, lambda s, r: s < 0.70 and r),
    ]
    from schemas.models import BRDInput
    dummy_brd = BRDInput(
        id="calibration-test",
        title="Calibration Test BRD",
        raw_content="This is a test BRD for critic calibration. " * 10,
        sections=[],
        metadata={"doc_type": "BRD", "domain": "fraud_detection", "complexity": "medium",
                  "problem_type": "new_feature", "author": "test", "tags": []},
    )
    for tier_name, fixture, pass_fn in tiers:
        output = critic_agent.run(
            brd_input=dummy_brd.model_dump(mode="json"),
            plan_output=fixture["plan_output"],
            architect_output=fixture["architect_output"],
            tech_stack_output=fixture["tech_stack_output"],
        )
        content = output.get("content") or {}
        score = content.get("overall_score", 0.0)
        revision = content.get("revision_required", False)
        passed = pass_fn(score, revision)
        results.append(CheckResult(
            f"calibration_{tier_name}_quality", passed, float(passed),
            f"score={score:.3f}, revision_required={revision}",
        ))
    return results


ALL_CHECKS = [
    check_all_five_dimensions_present,
    check_scores_in_range,
    check_overall_matches_weighted_formula,
    check_passed_consistent_with_score,
    check_revision_required_consistent,
    check_revision_notes_when_required,
    check_feedback_nonempty_per_dimension,
    check_schema_valid,
]
