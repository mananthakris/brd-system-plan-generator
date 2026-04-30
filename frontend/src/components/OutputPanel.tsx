import { Clock } from 'lucide-react'
import type { AgentOutput, NodeState, PipelineState } from '../types/pipeline'
import SolutionArchitectCard from './SolutionArchitectCard'
import PlanGeneratorCard from './PlanGeneratorCard'
import TechStackCard from './TechStackCard'
import ScheduleCard from './ScheduleCard'
import CriticCard from './CriticCard'
import ExecutiveSummaryCard from './ExecutiveSummaryCard'
import HitlCard from './HitlCard'

interface Props {
  pipeline: PipelineState
  sessionId: string
}

export default function OutputPanel({ pipeline, sessionId }: Props) {
  const { phase, nodes, brdTitle, brdMeta, error } = pipeline

  if (phase === 'rejected') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <p className="text-sm font-semibold text-red-700 mb-1">Plan rejected</p>
        <p className="text-sm text-red-600">The Engineering Manager rejected this plan. Submit a revised BRD to start a new run.</p>
      </div>
    )
  }

  if (phase === 'idle') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center mb-3">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 2L3 6V14L10 18L17 14V6L10 2Z" stroke="#4F46E5" strokeWidth="1.5" strokeLinejoin="round"/>
            <circle cx="10" cy="10" r="2" fill="#4F46E5"/>
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-500">
          Submit a BRD to generate a decision-ready engineering plan
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Supported formats: PDF · DOCX · Markdown · plain text
        </p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <p className="text-sm font-semibold text-red-700 mb-1">Pipeline error</p>
        <p className="text-sm text-red-600 font-mono">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* BRD summary bar */}
      {brdTitle && (
        <div className="bg-white border border-gray-200 rounded-xl px-5 py-3.5 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Processing</p>
            <p className="text-sm font-semibold text-gray-800">{brdTitle}</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            {brdMeta.sectionCount && (
              <span>{brdMeta.sectionCount} sections</span>
            )}
            {brdMeta.complexity && (
              <span className="capitalize">{brdMeta.complexity} complexity</span>
            )}
            {phase === 'complete' && (
              <span className="text-emerald-600 font-medium flex items-center gap-1">
                <Clock size={11} /> Complete
              </span>
            )}
          </div>
        </div>
      )}

      {/* Plan Generator — real output */}
      {nodes.plan_generator.status === 'complete' && nodes.plan_generator.output && (
        <PlanGeneratorCard output={extractAgentOutput(nodes.plan_generator, 'plan_output')} />
      )}

      {/* Solution Architect — real output */}
      {nodes.solution_architect.status === 'complete' && nodes.solution_architect.output && (
        <SolutionArchitectCard
          output={extractAgentOutput(nodes.solution_architect, 'architect_output')}
        />
      )}

      {/* Tech Stack Recommender — real output */}
      {nodes.tech_stack_recommender.status === 'complete' && nodes.tech_stack_recommender.output && (
        <TechStackCard output={extractAgentOutput(nodes.tech_stack_recommender, 'tech_stack_output')} />
      )}

      {/* Schedule Estimator — real output */}
      {nodes.schedule_estimator.status === 'complete' && nodes.schedule_estimator.output && (
        <ScheduleCard output={extractAgentOutput(nodes.schedule_estimator, 'schedule_output')} />
      )}

      {/* Critic — real output */}
      {nodes.critic.status === 'complete' && nodes.critic.output && (
        <CriticCard
          output={extractAgentOutput(nodes.critic, 'critic_output')}
          runCount={nodes.critic.runCount}
        />
      )}

      {/* HITL gate */}
      <HitlCard
        node={nodes.hitl}
        phase={phase}
        sessionId={sessionId}
        criticScore={
          (extractAgentOutput(nodes.critic, 'critic_output').content as Record<string, unknown>)
            ?.overall_score as number | undefined
        }
      />

      {/* Final engineering plan — real output */}
      {nodes.output.status === 'complete' && nodes.output.output && (
        <ExecutiveSummaryCard output={extractAgentOutput(nodes.output, 'engineering_plan')} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helper: pull the AgentOutput dict out of the node's state delta
// ---------------------------------------------------------------------------
function extractAgentOutput(node: NodeState, key: string): AgentOutput {
  const raw = (node.output ?? {}) as Record<string, unknown>
  return (raw[key] ?? {}) as AgentOutput
}
