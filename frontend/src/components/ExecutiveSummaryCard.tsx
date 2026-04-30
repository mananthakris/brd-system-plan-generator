import { FileText, RotateCcw } from 'lucide-react'
import type { AgentOutput, ProblemType } from '../types/pipeline'
import { PROBLEM_TYPE_LABELS, PROBLEM_TYPE_COLORS } from '../types/pipeline'

interface FinalPlan {
  title: string
  problem_type: ProblemType
  executive_summary: string
  revision_count: number
  critic_score: number | null
  critic_score_pct: number
  created_at: string
}

interface Props {
  output: AgentOutput
}

export default function ExecutiveSummaryCard({ output }: Props) {
  const plan = output.content as unknown as FinalPlan
  if (!plan?.executive_summary) return null

  const scoreColor =
    plan.critic_score_pct >= 85 ? 'text-emerald-600' :
    plan.critic_score_pct >= 70 ? 'text-indigo-600' :
    'text-amber-600'

  return (
    <div className="bg-white border-2 border-indigo-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 bg-indigo-50 border-b border-indigo-100 flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 bg-indigo-600 rounded-md flex items-center justify-center">
            <FileText size={13} className="text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-indigo-900">Engineering Plan — Ready</span>
            <p className="text-xs text-indigo-600 mt-0.5 truncate max-w-xs">{plan.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {plan.problem_type && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${PROBLEM_TYPE_COLORS[plan.problem_type]}`}>
              {PROBLEM_TYPE_LABELS[plan.problem_type]}
            </span>
          )}
          {plan.critic_score_pct > 0 && (
            <span className={`text-xs font-bold tabular-nums ${scoreColor}`}>
              {plan.critic_score_pct}/100
            </span>
          )}
        </div>
      </div>

      {/* Executive summary */}
      <div className="px-5 py-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">
          Executive Summary
        </p>
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
          {plan.executive_summary}
        </p>
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
        {plan.revision_count > 0 ? (
          <span className="flex items-center gap-1.5 text-xs text-amber-600">
            <RotateCcw size={11} />
            {plan.revision_count} revision cycle{plan.revision_count > 1 ? 's' : ''} by Critic
          </span>
        ) : (
          <span className="text-xs text-emerald-600">Passed quality review on first pass</span>
        )}
        <span className="text-xs text-gray-400">
          {plan.created_at ? new Date(plan.created_at).toLocaleTimeString() : ''}
        </span>
      </div>
    </div>
  )
}
