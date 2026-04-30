"""Custom Phoenix LLMEvaluator definitions for all 6 agents.

Evaluators are created via factory functions that accept a Phoenix LLM wrapper,
since LLMEvaluator requires the llm at construction time.

Usage:
    from evals.phoenix_evals.evaluators import build_evaluators_for_agent
    from phoenix.evals.llm import LLM

    from config import settings
    llm = LLM(provider="openai", model=settings.fast_model)
    evaluators = build_evaluators_for_agent("plan_generator", llm)
"""
from __future__ import annotations

from phoenix.evals import LLMEvaluator
from phoenix.evals.llm import LLM

# ---------------------------------------------------------------------------
# Prompt templates (plain strings, re-used across factory calls)
# ---------------------------------------------------------------------------

_PLAN_BRD_COVERAGE_TEMPLATE = """\
You are evaluating whether a generated project plan covers all functional requirements in the BRD.

BRD Content:
{input}

Generated Plan (phases and deliverables):
{output}

Score 1 if every major functional requirement from the BRD maps to at least one phase deliverable.
Score 0 if any functional requirement is missing from all phases.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the specific missing requirement, or confirming full coverage>
"""

_PLAN_PHASE_COHERENCE_TEMPLATE = """\
You are evaluating whether the phases in a project plan are in a logical sequence.

BRD Context:
{input}

Generated Plan Phases:
{output}

Score 1 if each phase naturally builds on the previous one and the ordering is logical for software delivery.
Score 0 if any phase appears out of order (e.g., integration before implementation, deployment before testing).

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the specific sequencing issue, or confirming logical order>
"""

_PLAN_SCOPE_RESPECT_TEMPLATE = """\
You are evaluating whether a project plan stays within the BRD's defined scope.

BRD Content (including any out-of-scope section):
{input}

Generated Plan:
{output}

Score 1 if no phase or deliverable addresses items explicitly marked out-of-scope in the BRD.
Score 0 if any phase or deliverable includes out-of-scope items.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the specific out-of-scope item included, or confirming scope is respected>
"""

_SCHEDULE_RISK_MITIGATION_TEMPLATE = """\
You are evaluating the quality of risk mitigation strategies in a project schedule.

BRD and Plan Context:
{input}

Schedule Risks:
{output}

Score 1 if every risk includes a specific, actionable mitigation strategy (not just "monitor" or "escalate").
Score 0 if any risk lacks a concrete mitigation or only states generic advice.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the specific risk that lacks proper mitigation, or confirming all risks are well-mitigated>
"""

_SCHEDULE_ASSUMPTION_SPECIFICITY_TEMPLATE = """\
You are evaluating whether planning assumptions in a project schedule are specific to the BRD.

BRD Content:
{input}

Schedule Assumptions:
{output}

Score 1 if every assumption references specific details from the BRD (team size, specific services, named constraints).
Score 0 if any assumption is generic and could apply to any project (e.g., "team will be fully staffed").

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the vague assumption, or confirming all assumptions are BRD-specific>
"""

_ARCHITECT_CLASSIFICATION_TEMPLATE = """\
You are evaluating whether an AI correctly classified the type of software problem described in a BRD.

BRD Content:
{input}

Classification Output (problem_type and rationale):
{output}

Valid problem types: greenfield, new_feature, migration, integration, poc, enhancement

Score 1 if the problem_type accurately reflects what the BRD is asking for, AND the rationale cites
specific evidence from the BRD (not generic reasoning).
Score 0 if the classification is wrong or the rationale is generic.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence explaining why the classification is correct or incorrect, citing specific BRD text>
"""

_ARCHITECT_OPTIONS_DIFFERENTIATED_TEMPLATE = """\
You are evaluating whether architectural options in a design proposal are meaningfully different.

BRD Context:
{input}

Architectural Options:
{output}

Score 1 if the options represent genuinely different architectural approaches (e.g., event-driven vs. batch,
serverless vs. containerised, microservice vs. monolith). Minor naming variations or the same approach
with different config do NOT count.
Score 0 if any two options are essentially the same approach with superficial differences.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing which options are too similar, or confirming meaningful differentiation>
"""

_ARCHITECT_RAG_GROUNDING_TEMPLATE = """\
You are evaluating whether an architecture design is grounded in the company's known technology stack.

The company (Arbor Risk) uses: Kafka, Aurora Postgres, EKS (Kubernetes), FastAPI, Python, AWS (no GCP/Azure),
Redis, Flink (in payment pipeline), Grafana/CloudWatch for monitoring.

BRD Context:
{input}

Architecture Output (components and integration points):
{output}

Score 1 if the recommended architecture's components reference specific services from Arbor's known stack
(not generic names like "message queue" or "database").
Score 0 if components are named generically without grounding in the actual company stack.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing a specific ungrounded component, or confirming stack alignment>
"""

_TECH_EXISTING_STACK_TEMPLATE = """\
You are evaluating whether a tech stack recommendation appropriately favours the company's existing services.

The company (Arbor Risk) already uses: Kafka, Aurora Postgres, EKS, FastAPI, Python 3.11, Redis, Flink,
AWS services (S3, EKS, RDS, CloudWatch). New services should only be introduced when there is no existing
alternative.

BRD and Architecture Context:
{input}

Tech Stack Recommendation:
{output}

Score 1 if the recommended option primarily extends existing Arbor services rather than introducing
net-new infrastructure or languages/frameworks the team doesn't use.
Score 0 if the recommendation introduces avoidable new services when existing alternatives exist.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the unnecessary new service, or confirming existing stack preference>
"""

_TECH_CONSTRAINT_RESPECT_TEMPLATE = """\
You are evaluating whether a tech stack recommendation respects all constraints stated in the BRD.

BRD Content (including constraints section):
{input}

Tech Stack Recommendation:
{output}

Score 1 if the recommended tech stack option respects ALL explicit constraints in the BRD
(e.g., AWS-only, Python-only, no Kafka if stated, latency SLAs, budget constraints).
Score 0 if any constraint is violated in the recommended option.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the violated constraint, or confirming all constraints are respected>
"""

_CRITIC_FEEDBACK_SPECIFICITY_TEMPLATE = """\
You are evaluating the quality of feedback produced by an AI critic reviewing an engineering plan.

Engineering Plan Being Reviewed:
{input}

Critic Feedback (per dimension):
{output}

Score 1 if every dimension's feedback cites a specific, concrete example from the plan
(e.g., naming a specific phase, component, or deliverable that caused the score).
Score 0 if any feedback is generic and could apply to any plan (e.g., "the plan could be more specific").

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing which dimension has generic feedback, or confirming all feedback is specific>
"""

_CRITIC_REVISION_NOTES_TEMPLATE = """\
You are evaluating whether revision notes from an AI critic are actionable.

Engineering Plan Context:
{input}

Critic Revision Notes:
{output}

Score 1 if each revision note tells the plan generator EXACTLY what to change
(e.g., "Add a specific deliverable for X in Phase 2", "Change the recommended architecture
option from A to B because of constraint Y").
Score 0 if any note is vague (e.g., "improve specificity", "add more detail").

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the vague note, or confirming all notes are actionable>
"""

_FORMATTER_BUSINESS_CLARITY_TEMPLATE = """\
You are evaluating whether an executive summary is clear and useful for an engineering manager.

Context (full engineering plan):
{input}

Executive Summary:
{output}

Score 1 if the summary:
  - Explains what is being built and why in plain language
  - States the timeline and team size clearly
  - Mentions the top 1-2 risks
  - Avoids jargon that a non-technical stakeholder would not understand
Score 0 if the summary is overly technical, vague, or missing key information.

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing what is missing or unclear, or confirming the summary is EM-ready>
"""

_FORMATTER_TECHNICAL_ACCURACY_TEMPLATE = """\
You are evaluating whether an executive summary accurately reflects the technical decisions in the plan.

Full Engineering Plan (architecture, tech stack, schedule):
{input}

Executive Summary:
{output}

Score 1 if the summary accurately describes the recommended architecture option,
the recommended tech stack, and the timeline from the schedule.
Score 0 if the summary misrepresents any of these (wrong tech, wrong timeline, wrong architecture approach).

Respond with exactly:
Score: <0 or 1>
Explanation: <one sentence citing the inaccuracy, or confirming the summary is technically accurate>
"""

# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

_AGENT_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "plan_generator": [
        ("plan_brd_coverage", _PLAN_BRD_COVERAGE_TEMPLATE),
        ("plan_phase_coherence", _PLAN_PHASE_COHERENCE_TEMPLATE),
        ("plan_scope_respect", _PLAN_SCOPE_RESPECT_TEMPLATE),
    ],
    "schedule_estimator": [
        ("schedule_risk_mitigation_quality", _SCHEDULE_RISK_MITIGATION_TEMPLATE),
        ("schedule_assumption_specificity", _SCHEDULE_ASSUMPTION_SPECIFICITY_TEMPLATE),
    ],
    "solution_architect": [
        ("architect_classification_accuracy", _ARCHITECT_CLASSIFICATION_TEMPLATE),
        ("architect_options_genuinely_different", _ARCHITECT_OPTIONS_DIFFERENTIATED_TEMPLATE),
        ("architect_rag_grounding", _ARCHITECT_RAG_GROUNDING_TEMPLATE),
    ],
    "tech_stack_recommender": [
        ("tech_existing_stack_preference", _TECH_EXISTING_STACK_TEMPLATE),
        ("tech_constraint_respect", _TECH_CONSTRAINT_RESPECT_TEMPLATE),
    ],
    "critic": [
        ("critic_feedback_specificity", _CRITIC_FEEDBACK_SPECIFICITY_TEMPLATE),
        ("critic_revision_notes_actionability", _CRITIC_REVISION_NOTES_TEMPLATE),
    ],
    "output_formatter": [
        ("formatter_business_clarity", _FORMATTER_BUSINESS_CLARITY_TEMPLATE),
        ("formatter_technical_accuracy", _FORMATTER_TECHNICAL_ACCURACY_TEMPLATE),
    ],
}


def build_evaluators_for_agent(agent_name: str, llm: LLM) -> list[LLMEvaluator]:
    templates = _AGENT_TEMPLATES.get(agent_name, [])
    return [
        LLMEvaluator(name=name, llm=llm, prompt_template=template)
        for name, template in templates
    ]


def build_all_evaluators(llm: LLM) -> dict[str, list[LLMEvaluator]]:
    return {
        agent: build_evaluators_for_agent(agent, llm)
        for agent in _AGENT_TEMPLATES
    }


AGENT_NAMES = list(_AGENT_TEMPLATES.keys())
