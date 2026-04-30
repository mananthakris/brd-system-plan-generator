from __future__ import annotations

import operator
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocType(str, Enum):
    BRD = "brd"
    PRD = "prd"
    RFC = "rfc"
    ADR = "adr"
    OTHER = "other"


class ProblemType(str, Enum):
    GREENFIELD = "greenfield"    # entirely new standalone product or system
    NEW_FEATURE = "new_feature"  # net-new capability in an existing product (nothing to extend)
    MIGRATION = "migration"      # moving from one technology or platform to another
    INTEGRATION = "integration"  # connecting existing systems via APIs or event streams
    POC = "poc"                  # time-boxed spike to validate before full build
    ENHANCEMENT = "enhancement"  # improving or extending functionality that already exists


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Ingestion layer
# ---------------------------------------------------------------------------

class BRDSection(BaseModel):
    section_type: str  # objective | requirements | constraints | stakeholders |
                       # success_criteria | timeline | budget | risks | out_of_scope
    title: str
    content: str


class BRDMetadata(BaseModel):
    doc_type: DocType
    domain: str
    complexity: ComplexityLevel
    problem_type: Optional[ProblemType] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    version: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class BRDInput(BaseModel):
    id: str
    title: str
    raw_content: str
    sections: list[BRDSection] = Field(default_factory=list)
    metadata: BRDMetadata
    context_docs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

class RAGContext(BaseModel):
    query: str
    retrieved_chunks: list[str]
    sources: list[str]
    scores: list[float]


# ---------------------------------------------------------------------------
# Agent I/O
# ---------------------------------------------------------------------------

class AgentOutput(BaseModel):
    agent_name: str
    content: dict[str, Any]
    raw_text: str
    rag_context: Optional[RAGContext] = None
    model_used: str
    tokens_used: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Critic rubric
# ---------------------------------------------------------------------------

class CriticDimension(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    passed: bool


class CriticRubric(BaseModel):
    completeness: CriticDimension
    feasibility: CriticDimension
    specificity: CriticDimension
    consistency: CriticDimension
    scope_fit: CriticDimension
    overall_score: float = Field(ge=0.0, le=1.0)
    revision_required: bool
    revision_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Planning agents output
# ---------------------------------------------------------------------------

class PlanPhase(BaseModel):
    phase_number: int
    name: str
    objectives: list[str]
    deliverables: list[str]
    duration_weeks: int
    dependencies: list[str] = Field(default_factory=list)


class ScheduleEstimate(BaseModel):
    total_weeks: int
    total_engineers: int
    phases: list[PlanPhase]
    assumptions: list[str]
    risks: list[str]


# ---------------------------------------------------------------------------
# Design agents output — multi-option architecture
# ---------------------------------------------------------------------------

class ArchitectureOption(BaseModel):
    option_id: str          # "A", "B", "C"
    name: str               # short descriptive name, e.g. "Streaming-first with Kafka + Feature Store"
    description: str        # 1-3 sentence summary of the approach
    high_level_components: list[str]
    data_flow: str
    integration_points: list[str]
    constraints_addressed: list[str]
    trade_offs: str         # concise pros/cons narrative
    estimated_complexity: str  # "low" | "medium" | "high"


class ArchitectureDesign(BaseModel):
    problem_type: ProblemType
    classification_rationale: str
    options: list[ArchitectureOption]
    recommended_option_id: str        # "A", "B", or "C"
    recommendation_rationale: str


class TechOption(BaseModel):
    name: str
    rationale: str
    pros: list[str]
    cons: list[str]
    estimated_effort: str


class TechStackRecommendation(BaseModel):
    options: list[TechOption]
    recommended: str
    rationale: str


class PoCPlan(BaseModel):
    scope: str
    success_criteria: list[str]
    duration_weeks: int
    team_size: int
    key_risks: list[str]
    out_of_scope: list[str]


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------

class EngineeringPlan(BaseModel):
    id: str
    brd_id: str
    title: str
    problem_type: ProblemType
    executive_summary: str
    architecture: ArchitectureDesign
    schedule: ScheduleEstimate
    tech_stack: TechStackRecommendation
    poc_plan: Optional[PoCPlan] = None
    revision_count: int = 0
    critic_score: Optional[float] = None
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# LangGraph state (TypedDict — required for LangGraph state graph)
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    brd_input: Optional[dict]           # serialised BRDInput
    rag_context: dict                    # keyed by agent name
    plan_output: Optional[dict]
    schedule_output: Optional[dict]
    architect_output: Optional[dict]
    poc_output: Optional[dict]
    tech_stack_output: Optional[dict]
    critic_output: Optional[dict]
    engineering_plan: Optional[dict]
    revision_count: int
    hitl_approved: bool
    errors: Annotated[list[str], operator.add]  # reducer: append-only
