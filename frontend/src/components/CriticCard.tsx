import { ShieldCheck, ShieldAlert, RotateCcw, AlertTriangle } from 'lucide-react'
import type { AgentOutput, CriticRubric, CriticDimension } from '../types/pipeline'

interface Props {
  output: AgentOutput
  runCount: number
}

const DIMENSION_LABELS: Record<keyof Pick<CriticRubric, 'completeness' | 'feasibility' | 'specificity' | 'consistency' | 'scope_fit'>, string> = {
  completeness: 'Completeness',
  feasibility:  'Feasibility',
  specificity:  'Specificity',
  consistency:  'Consistency',
  scope_fit:    'Scope Fit',
}

export default function CriticCard({ output, runCount }: Props) {
  const rubric = output.content as CriticRubric
  if (rubric?.overall_score === undefined) return null

  const pct = Math.round(rubric.overall_score * 100)
  const passed = !rubric.revision_required

  const scoreColor =
    pct >= 85 ? 'text-emerald-600' :
    pct >= 70 ? 'text-indigo-600' :
    pct >= 55 ? 'text-amber-600' : 'text-red-600'

  const scoreBg =
    pct >= 85 ? 'bg-emerald-50 border-emerald-200' :
    pct >= 70 ? 'bg-indigo-50 border-indigo-200' :
    pct >= 55 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`w-6 h-6 rounded-md flex items-center justify-center ${passed ? 'bg-emerald-100' : 'bg-amber-100'}`}>
            {passed
              ? <ShieldCheck size={13} className="text-emerald-600" />
              : <ShieldAlert size={13} className="text-amber-600" />
            }
          </div>
          <span className="text-sm font-semibold text-gray-800">Quality Review</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <RotateCcw size={11} />
          <span>{runCount} pass{runCount !== 1 ? 'es' : ''}</span>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Overall score */}
        <div className={`flex items-center justify-between px-4 py-3 rounded-xl border ${scoreBg}`}>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Overall score</p>
            <p className={`text-2xl font-bold tabular-nums ${scoreColor}`}>{pct}<span className="text-sm font-normal">/100</span></p>
          </div>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
            passed
              ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
              : 'bg-amber-100 text-amber-700 border-amber-200'
          }`}>
            {passed ? 'Passed' : 'Needs revision'}
          </span>
        </div>

        {/* Dimension scores */}
        <div className="space-y-2">
          {(Object.keys(DIMENSION_LABELS) as Array<keyof typeof DIMENSION_LABELS>).map((key) => (
            <DimensionRow key={key} label={DIMENSION_LABELS[key]} dim={rubric[key]} />
          ))}
        </div>

        {/* Revision notes */}
        {rubric.revision_notes && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={12} className="text-amber-600" />
              <span className="text-xs font-semibold text-amber-800">Revision notes</span>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed whitespace-pre-line">
              {rubric.revision_notes}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function DimensionRow({ label, dim }: { label: string; dim: CriticDimension }) {
  const pct = Math.round(dim.score * 100)
  const barColor = dim.passed
    ? pct >= 85 ? 'bg-emerald-500' : 'bg-indigo-500'
    : 'bg-amber-500'

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-medium tabular-nums w-8 text-right ${
        dim.passed ? 'text-gray-700' : 'text-amber-600'
      }`}>
        {pct}
      </span>
      <span className="text-xs text-gray-300 w-48 shrink-0 truncate">{dim.feedback}</span>
    </div>
  )
}
