import type { NodeName, PipelineState } from '../types/pipeline'
import { NODE_META, NODE_ORDER } from '../types/pipeline'
import NodeStatusItem from './NodeStatusItem'
import { RotateCcw } from 'lucide-react'

interface Props {
  pipeline: PipelineState
  isStarting?: boolean
}

export default function PipelineStatus({ pipeline, isStarting = false }: Props) {
  const { nodes, revisionCount, phase } = pipeline

  // Track which groups we've already rendered a label for
  const seenGroups = new Set<string>()

  return (
    <aside className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col h-full overflow-y-auto">
      <div className="px-4 py-4 border-b border-gray-100">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
          Pipeline
        </h2>
        {isStarting && phase === 'idle' && (
          <p className="mt-0.5 text-xs text-blue-400 font-medium flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            Starting…
          </p>
        )}
        {phase === 'running' && (
          <p className="mt-0.5 text-xs text-blue-500 font-medium">Running…</p>
        )}
        {phase === 'hitl_pending' && (
          <p className="mt-0.5 text-xs text-amber-600 font-medium flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            Awaiting approval…
          </p>
        )}
        {phase === 'complete' && (
          <p className="mt-0.5 text-xs text-emerald-600 font-medium">Complete</p>
        )}
        {phase === 'rejected' && (
          <p className="mt-0.5 text-xs text-red-500 font-medium">Rejected</p>
        )}
        {phase === 'error' && (
          <p className="mt-0.5 text-xs text-red-500 font-medium">Error</p>
        )}
        {nodes.critic.runCount > 0 && (
          <p className="mt-1 text-xs text-indigo-600 font-medium flex items-center gap-1">
            <RotateCcw size={10} />
            Critic: {nodes.critic.runCount} pass{nodes.critic.runCount > 1 ? 'es' : ''}
            {revisionCount > 0 && ` · ${revisionCount} revision${revisionCount > 1 ? 's' : ''}`}
          </p>
        )}
      </div>

      <nav className="flex-1 py-2">
        {NODE_ORDER.map((name) => {
          const meta = NODE_META[name]
          const isFirstInGroup = !seenGroups.has(meta.group)
          if (isFirstInGroup) seenGroups.add(meta.group)

          return (
            <NodeStatusItem
              key={name}
              label={meta.label}
              status={nodes[name as NodeName].status}
              meta={meta}
              isFirstInGroup={isFirstInGroup}
              runCount={nodes[name as NodeName].runCount}
            />
          )
        })}
      </nav>

      {phase === 'idle' && !isStarting && (
        <div className="px-4 py-4 border-t border-gray-100">
          <p className="text-[11px] text-gray-400 leading-relaxed">
            Submit a BRD to start the pipeline.
          </p>
        </div>
      )}
    </aside>
  )
}
