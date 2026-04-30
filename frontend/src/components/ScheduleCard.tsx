import { CalendarDays, Users, AlertTriangle, CheckCircle2 } from 'lucide-react'
import type { AgentOutput } from '../types/pipeline'

interface ScheduleEstimate {
  total_weeks: number
  total_engineers: number
  phases: unknown[]
  assumptions: string[]
  risks: string[]
}

interface Props {
  output: AgentOutput
}

export default function ScheduleCard({ output }: Props) {
  const sched = output.content as unknown as ScheduleEstimate
  if (!sched?.total_weeks) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 bg-indigo-100 rounded-md flex items-center justify-center">
            <CalendarDays size={13} className="text-indigo-600" />
          </div>
          <span className="text-sm font-semibold text-gray-800">Schedule</span>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <span className="flex items-center gap-1 text-indigo-700 bg-indigo-50 border border-indigo-100 px-2.5 py-1 rounded-full">
            <CalendarDays size={10} />
            {sched.total_weeks}w
          </span>
          <span className="flex items-center gap-1 text-gray-600 bg-gray-50 border border-gray-100 px-2.5 py-1 rounded-full">
            <Users size={10} />
            {sched.total_engineers} engineers
          </span>
        </div>
      </div>

      <div className="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Assumptions */}
        {sched.assumptions?.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-2">
              Assumptions
            </p>
            <ul className="space-y-1.5">
              {sched.assumptions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                  <CheckCircle2 size={11} className="text-indigo-400 shrink-0 mt-0.5" />
                  {a}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risks */}
        {sched.risks?.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-500 mb-2">
              Schedule risks
            </p>
            <ul className="space-y-1.5">
              {sched.risks.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                  <AlertTriangle size={11} className="text-amber-500 shrink-0 mt-0.5" />
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
