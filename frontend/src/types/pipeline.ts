// Mirrors Python schemas/models.py — keep in sync when models change

export type ProblemType =
  | 'greenfield'
  | 'new_feature'
  | 'migration'
  | 'integration'
  | 'poc'
  | 'enhancement'

export type NodeName =
  | 'ingest'
  | 'plan_generator'
  | 'schedule_estimator'
  | 'solution_architect'
  | 'poc_planner'
  | 'tech_stack_recommender'
  | 'critic'
  | 'hitl'
  | 'output'

export type NodeStatus = 'pending' | 'running' | 'complete' | 'stub' | 'error'

// ---------------------------------------------------------------------------
// SSE event shapes emitted by /api/stream/{session_id}
// ---------------------------------------------------------------------------

export interface PipelineStartEvent {
  type: 'pipeline_start'
  session_id: string
  brd_title: string
  brd_id: string
  problem_type_hint: ProblemType | null
  complexity: 'low' | 'medium' | 'high'
  section_count: number
  timestamp: string
}

export interface NodeCompleteEvent {
  type: 'node_complete'
  node: NodeName
  is_stub: boolean
  output: Record<string, unknown>
  revision_count: number
  timestamp: string
}

export interface PipelineCompleteEvent {
  type: 'pipeline_complete'
  timestamp: string
}

export interface PipelineErrorEvent {
  type: 'error'
  message: string
  timestamp: string
}

export interface HitlPendingEvent {
  type: 'hitl_pending'
  timestamp: string
}

export interface PipelineRejectedEvent {
  type: 'pipeline_rejected'
  timestamp: string
}

export type PipelineEvent =
  | PipelineStartEvent
  | NodeCompleteEvent
  | PipelineCompleteEvent
  | PipelineErrorEvent
  | HitlPendingEvent
  | PipelineRejectedEvent

// ---------------------------------------------------------------------------
// Architecture design output — multi-option (from solution_architect agent)
// ---------------------------------------------------------------------------

export interface ArchitectureOption {
  option_id: string              // "A", "B", "C"
  name: string
  description: string
  high_level_components: string[]
  data_flow: string
  integration_points: string[]
  constraints_addressed: string[]
  trade_offs: string
  estimated_complexity: 'low' | 'medium' | 'high'
}

export interface ArchitectureDesign {
  problem_type: ProblemType
  classification_rationale: string
  options: ArchitectureOption[]
  recommended_option_id: string
  recommendation_rationale: string
}

// ---------------------------------------------------------------------------
// Plan Generator output
// ---------------------------------------------------------------------------

export interface PlanPhase {
  phase_number: number
  name: string
  objectives: string[]
  deliverables: string[]
  duration_weeks: number
  dependencies: string[]
}

export interface PlanOutput {
  project_overview: string
  phases: PlanPhase[]
  key_milestones: string[]
  total_phases: number
  total_weeks_estimate: number
}

// ---------------------------------------------------------------------------
// Tech Stack Recommender output
// ---------------------------------------------------------------------------

export interface TechOption {
  name: string
  rationale: string
  pros: string[]
  cons: string[]
  estimated_effort: string
}

export interface TechStackRecommendation {
  options: TechOption[]
  recommended: string
  rationale: string
}

// ---------------------------------------------------------------------------
// Critic output
// ---------------------------------------------------------------------------

export interface CriticDimension {
  name: string
  score: number
  feedback: string
  passed: boolean
}

export interface CriticRubric {
  completeness: CriticDimension
  feasibility: CriticDimension
  specificity: CriticDimension
  consistency: CriticDimension
  scope_fit: CriticDimension
  overall_score: number
  revision_required: boolean
  revision_notes: string | null
}

// ---------------------------------------------------------------------------
// Generic AgentOutput wrapper
// ---------------------------------------------------------------------------

export interface AgentOutput {
  agent_name: string
  content: ArchitectureDesign | PlanOutput | TechStackRecommendation | CriticRubric | Record<string, unknown>
  raw_text: string
  rag_context?: {
    retrieved_chunks: string[]
    sources: string[]
    scores: number[]
  }
  model_used: string
  tokens_used?: number
  created_at: string
}

// ---------------------------------------------------------------------------
// Derived UI state
// ---------------------------------------------------------------------------

export interface NodeState {
  status: NodeStatus
  isStub: boolean
  output: Record<string, unknown> | null
  completedAt: string | null
  revisionCount: number
  runCount: number   // how many times this specific node fired (≥1 for critic when it loops)
}

export interface PipelineState {
  phase: 'idle' | 'running' | 'hitl_pending' | 'complete' | 'rejected' | 'error'
  brdTitle: string | null
  brdMeta: {
    problemTypeHint: ProblemType | null
    complexity: string | null
    sectionCount: number | null
  }
  nodes: Record<NodeName, NodeState>
  revisionCount: number
  error: string | null
}

// ---------------------------------------------------------------------------
// Node display metadata (static)
// ---------------------------------------------------------------------------

export interface NodeMeta {
  label: string
  group: 'input' | 'planning' | 'design' | 'quality' | 'review' | 'output'
  conditional?: boolean // poc_planner only runs for poc problem type
}

export const NODE_META: Record<NodeName, NodeMeta> = {
  ingest:                 { label: 'BRD Ingestion',          group: 'input' },
  plan_generator:         { label: 'Plan Generator',          group: 'planning' },
  schedule_estimator:     { label: 'Schedule Estimator',      group: 'planning' },
  solution_architect:     { label: 'Solution Architect',      group: 'design' },
  tech_stack_recommender: { label: 'Tech Stack Recommender',  group: 'design' },
  poc_planner:            { label: 'PoC Planner',             group: 'design', conditional: true },
  critic:                 { label: 'Critic Agent',            group: 'quality' },
  hitl:                   { label: 'HITL Gate',               group: 'review' },
  output:                 { label: 'Decision-ready Design',   group: 'output' },
}

// Ordered list — drives both the status panel and "next running" inference
// Order matches v3 diagram: ingest → planning group → design group (SA → tech stack → PoC) → critic → hitl → output
export const NODE_ORDER: NodeName[] = [
  'ingest',
  'plan_generator',
  'solution_architect',
  'tech_stack_recommender',
  'poc_planner',
  'schedule_estimator',
  'critic',
  'hitl',
  'output',
]

export const INITIAL_NODE_STATE: NodeState = {
  status: 'pending',
  isStub: false,
  output: null,
  completedAt: null,
  revisionCount: 0,
  runCount: 0,
}

export const PROBLEM_TYPE_LABELS: Record<ProblemType, string> = {
  greenfield:  'Greenfield',
  new_feature: 'New Feature',
  migration:   'Migration',
  integration: 'Integration',
  poc:         'Proof of Concept',
  enhancement: 'Enhancement',
}

export const PROBLEM_TYPE_COLORS: Record<ProblemType, string> = {
  greenfield:  'bg-blue-100 text-blue-800 border-blue-200',
  new_feature: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  migration:   'bg-amber-100 text-amber-800 border-amber-200',
  integration: 'bg-violet-100 text-violet-800 border-violet-200',
  poc:         'bg-orange-100 text-orange-800 border-orange-200',
  enhancement: 'bg-sky-100 text-sky-800 border-sky-200',
}

export const COMPLEXITY_COLORS: Record<'low' | 'medium' | 'high', string> = {
  low:    'bg-green-100 text-green-700 border-green-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  high:   'bg-red-100 text-red-700 border-red-200',
}
