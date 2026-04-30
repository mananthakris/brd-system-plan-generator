import { CheckCircle2, Circle, Loader2, MinusCircle, XCircle, RotateCcw } from 'lucide-react'
import type { NodeMeta, NodeStatus } from '../types/pipeline'

interface Props {
  label: string
  status: NodeStatus
  meta: NodeMeta
  isFirstInGroup: boolean
  groupLabel?: string
  runCount?: number
}

const GROUP_LABELS: Record<NodeMeta['group'], string> = {
  input:   'Ingestion',
  planning: 'Planning',
  design:   'Design',
  quality:  'Quality loop',
  review:   'Review',
  output:   'Output',
}

export default function NodeStatusItem({ label, status, meta, isFirstInGroup, groupLabel, runCount }: Props) {
  return (
    <div>
      {isFirstInGroup && (
        <div className="mt-4 mb-1 px-3">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">
            {groupLabel ?? GROUP_LABELS[meta.group]}
          </span>
        </div>
      )}
      <div className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md mx-1 ${
        status === 'running' ? 'bg-blue-50' : ''
      }`}>
        <Icon status={status} />
        <span className={`text-sm leading-tight ${labelColor(status)}`}>
          {label}
        </span>
        {status === 'stub' && (
          <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 border border-gray-200">
            stub
          </span>
        )}
        {meta.conditional && status === 'pending' && (
          <span className="ml-auto text-[10px] text-gray-300">conditional</span>
        )}
        {meta.group === 'quality' && runCount != null && runCount > 1 && status !== 'stub' && (
          <span className="ml-auto flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">
            <RotateCcw size={9} />
            {runCount}×
          </span>
        )}
      </div>
    </div>
  )
}

function Icon({ status }: { status: NodeStatus }) {
  switch (status) {
    case 'complete':
      return <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
    case 'stub':
      return <MinusCircle size={15} className="text-gray-300 shrink-0" />
    case 'running':
      return <Loader2 size={15} className="text-blue-500 shrink-0 animate-spin-slow" />
    case 'error':
      return <XCircle size={15} className="text-red-400 shrink-0" />
    default:
      return <Circle size={15} className="text-gray-200 shrink-0" />
  }
}

function labelColor(status: NodeStatus): string {
  switch (status) {
    case 'complete': return 'text-gray-800 font-medium'
    case 'stub':     return 'text-gray-400'
    case 'running':  return 'text-blue-700 font-medium'
    case 'error':    return 'text-red-500'
    default:         return 'text-gray-400'
  }
}
