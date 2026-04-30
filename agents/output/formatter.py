"""Output formatter agent.

Generates an executive summary from all upstream agent outputs and assembles
the final engineering plan dict. The summary is 2-3 prose paragraphs suitable
for sharing with an engineering manager.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from opentelemetry import trace as otel_trace
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from schemas.models import AgentOutput, BRDInput


# ---------------------------------------------------------------------------
# Internal structured output schema
# ---------------------------------------------------------------------------

class _SummaryOutput(BaseModel):
    executive_summary: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SUMMARY_SYSTEM = """\
You are a technical writer producing an executive summary of a completed engineering plan.

Write 2-3 paragraphs (150-250 words total) that an engineering manager could share with
stakeholders or include in a planning document.

Paragraph 1: What is being built and why — the business problem and what the plan delivers.
Paragraph 2: The recommended technical approach — the architecture option and tech stack chosen, and why.
Paragraph 3: Delivery expectations — timeline, team size, and the top 1-2 risks to watch.

Rules:
- Prose only — no bullet points, no headers
- Direct and technical but not jargon-heavy
- No marketing language or excessive hedging
- State the recommended approach clearly; do not present all options
"""

_SUMMARY_USER = """\
BRD title: {title}
Objective: {objective}

Recommended architecture: {arch_summary}
Recommended tech stack: {tech_summary}
Timeline: {total_weeks} weeks · {total_engineers} engineers
Top risks: {risks}
Quality score: {critic_score}/100 (after {revision_count} revision cycle(s))
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class OutputFormatterAgent:
    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.fast_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(
        self,
        brd_input: dict,
        plan_output: dict | None,
        architect_output: dict | None,
        tech_stack_output: dict | None,
        schedule_output: dict | None,
        critic_output: dict | None,
        revision_count: int,
    ) -> dict:
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "output_formatter")
        _span.set_attribute("brd.id", brd.id)
        summary, tokens = self._generate_summary(
            brd, architect_output, tech_stack_output, schedule_output, critic_output, revision_count,
        )

        critic_score = ((critic_output or {}).get("content") or {}).get("overall_score")

        plan = {
            "id": str(uuid.uuid4()),
            "brd_id": brd.id,
            "title": f"Engineering Plan: {brd.title}",
            "problem_type": ((architect_output or {}).get("content") or {}).get("problem_type", "enhancement"),
            "executive_summary": summary.executive_summary,
            "architecture": (architect_output or {}).get("content", {}),
            "schedule": (schedule_output or {}).get("content", {}),
            "tech_stack": (tech_stack_output or {}).get("content", {}),
            "revision_count": revision_count,
            "critic_score": critic_score,
            "critic_score_pct": round((critic_score or 0) * 100),
            "created_at": datetime.utcnow().isoformat(),
        }

        output = AgentOutput(
            agent_name="output",
            content=plan,
            raw_text=summary.executive_summary,
            model_used=settings.fast_model,
            tokens_used=tokens,
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------

    def _generate_summary(
        self,
        brd: BRDInput,
        architect_output: dict | None,
        tech_stack_output: dict | None,
        schedule_output: dict | None,
        critic_output: dict | None,
        revision_count: int,
    ) -> tuple[_SummaryOutput, int | None]:
        llm = self._llm.with_structured_output(_SummaryOutput, include_raw=True)

        arch_content = (architect_output or {}).get("content", {})
        options = arch_content.get("options", [])
        rec_id = arch_content.get("recommended_option_id", "")
        rec_arch = next((o for o in options if o.get("option_id") == rec_id), None)
        arch_summary = (
            f"{rec_arch['name']}: {rec_arch['description']}" if rec_arch else "(not available)"
        )

        tech_content = (tech_stack_output or {}).get("content", {})
        recommended_tech = tech_content.get("recommended", "")
        tech_options = tech_content.get("options", [])
        rec_tech = next((o for o in tech_options if o.get("name") == recommended_tech), None)
        tech_summary = (
            f"{recommended_tech}: {rec_tech.get('rationale', '')}" if rec_tech else recommended_tech
        )

        sched_content = (schedule_output or {}).get("content", {})
        total_weeks = sched_content.get("total_weeks", 0)
        total_engineers = sched_content.get("total_engineers", 0)
        risks = "; ".join(sched_content.get("risks", [])[:2]) or "none identified"

        critic_content = (critic_output or {}).get("content", {})
        critic_score_pct = round((critic_content.get("overall_score") or 0) * 100)

        objective = next(
            (s.content for s in brd.sections if s.section_type == "objective"),
            brd.raw_content[:300],
        )

        user_content = _SUMMARY_USER.format(
            title=brd.title,
            objective=objective[:500],
            arch_summary=arch_summary,
            tech_summary=tech_summary,
            total_weeks=total_weeks,
            total_engineers=total_engineers,
            risks=risks,
            critic_score=critic_score_pct,
            revision_count=revision_count,
        )

        result = llm.invoke([
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user", "content": user_content},
        ])
        parsed: _SummaryOutput = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_tokens(raw_message) -> int | None:
    try:
        usage = raw_message.response_metadata.get("token_usage", {})
        return usage.get("total_tokens")
    except Exception:
        return None
