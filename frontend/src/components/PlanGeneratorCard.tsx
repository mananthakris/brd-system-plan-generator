import { CheckCircle2, Clock, ChevronRight } from 'lucide-react'
import type { AgentOutput, PlanOutput } from '../types/pipeline'

interface Props {
  output: AgentOutput
}

export default function PlanGeneratorCard({ output }: Props) {
  const plan = output.content as PlanOutput
  if (!plan?.phases) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 bg-indigo-100 rounded-md flex items-center justify-center">
            <Clock size={13} className="text-indigo-600" />
          </div>
          <span className="text-sm font-semibold text-gray-800">Project Plan</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span>{plan.total_phases} phases</span>
          <span>·</span>
          <span>{plan.total_weeks_estimate}w estimated</span>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Overview */}
        <p className="text-sm text-gray-600 leading-relaxed">{plan.project_overview}</p>

        {/* Phases */}
        <div className="space-y-2">
          {plan.phases.map((phase) => (
            <PhaseRow key={phase.phase_number} phase={phase} />
          ))}
        </div>

        {/* Milestones */}
        {plan.key_milestones?.length > 0 && (
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3">
            <p className="text-xs font-semibold text-indigo-700 mb-2 uppercase tracking-wide">
              Key milestones
            </p>
            <ul className="space-y-1">
              {plan.key_milestones.map((m, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-indigo-800">
                  <ChevronRight size={11} className="shrink-0 mt-0.5 text-indigo-400" />
                  {m}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

function PhaseRow({ phase }: { phase: PlanOutput['phases'][number] }) {
  return (
    <details className="group bg-gray-50 border border-gray-100 rounded-xl">
      <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer list-none select-none">
        <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">
          {phase.phase_number}
        </span>
        <span className="text-sm font-medium text-gray-800 flex-1">{phase.name}</span>
        <span className="text-xs text-gray-400 shrink-0">{phase.duration_weeks}w</span>
        <ChevronRight size={13} className="text-gray-400 transition-transform group-open:rotate-90 shrink-0" />
      </summary>

      <div className="px-4 pb-4 pt-1 space-y-3 border-t border-gray-100">
        {/* Objectives */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1.5">
            Objectives
          </p>
          <ul className="space-y-1">
            {phase.objectives.map((obj, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                <span className="text-indigo-400 mt-0.5 shrink-0">•</span>
                {obj}
              </li>
            ))}
          </ul>
        </div>

        {/* Deliverables */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1.5">
            Deliverables
          </p>
          <ul className="space-y-1">
            {phase.deliverables.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                <CheckCircle2 size={11} className="text-emerald-500 mt-0.5 shrink-0" />
                {d}
              </li>
            ))}
          </ul>
        </div>

        {/* Dependencies */}
        {phase.dependencies?.length > 0 && (
          <p className="text-xs text-gray-400">
            Depends on: {phase.dependencies.join(', ')}
          </p>
        )}
      </div>
    </details>
  )
}
