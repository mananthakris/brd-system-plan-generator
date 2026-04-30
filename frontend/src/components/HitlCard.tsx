import { useState } from 'react'
import { UserCheck, UserX, Info, Loader2 } from 'lucide-react'
import type { NodeState, PipelineState } from '../types/pipeline'

interface Props {
  node: NodeState
  phase: PipelineState['phase']
  sessionId: string
  criticScore?: number
}

export default function HitlCard({ node, phase, sessionId, criticScore }: Props) {
  const [submitting, setSubmitting] = useState(false)

  const scoreText = criticScore != null
    ? `Quality score: ${Math.round(criticScore * 100)}/100`
    : null

  // Show the card when the pipeline is paused at HITL, or when the node has completed
  const visible = phase === 'hitl_pending' || node.status === 'complete'
  if (!visible) return null

  async function decide(approved: boolean) {
    setSubmitting(true)
    try {
      await fetch(`/api/hitl/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      })
    } catch {
      setSubmitting(false)
    }
  }

  if (phase === 'hitl_pending') {
    return (
      <div className="bg-white border border-amber-200 rounded-xl px-5 py-4">
        <div className="flex items-start gap-4">
          <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
            <UserCheck size={16} className="text-amber-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-sm font-semibold text-gray-800">HITL Gate</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200 animate-pulse">
                Awaiting review
              </span>
            </div>
            <p className="text-xs text-gray-400 flex items-center gap-1 mb-3">
              <Info size={10} className="shrink-0" />
              Engineering Manager review required before delivering the plan
              {scoreText && ` · ${scoreText}`}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => decide(true)}
                disabled={submitting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? <Loader2 size={12} className="animate-spin" /> : <UserCheck size={12} />}
                Approve
              </button>
              <button
                onClick={() => decide(false)}
                disabled={submitting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-100 text-red-700 border border-red-200 hover:bg-red-200 disabled:opacity-50 transition-colors"
              >
                {submitting ? <Loader2 size={12} className="animate-spin" /> : <UserX size={12} />}
                Reject
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // node.status === 'complete' — approved
  return (
    <div className="bg-white border border-emerald-200 rounded-xl px-5 py-4 flex items-center gap-4">
      <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center shrink-0">
        <UserCheck size={16} className="text-emerald-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-800">HITL Gate</span>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
            Approved
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
          <Info size={10} className="shrink-0" />
          Engineering Manager approved — generating final plan
          {scoreText && ` · ${scoreText}`}
        </p>
      </div>
    </div>
  )
}
