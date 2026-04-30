import { useEffect, useReducer, useRef } from 'react'
import type {
  NodeName,
  NodeState,
  PipelineEvent,
  PipelineState,
} from '../types/pipeline'
import {
  INITIAL_NODE_STATE,
  NODE_ORDER,
} from '../types/pipeline'

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

function makeInitialState(): PipelineState {
  const nodes = {} as Record<NodeName, NodeState>
  for (const n of NODE_ORDER) {
    nodes[n] = { ...INITIAL_NODE_STATE }
  }
  return {
    phase: 'idle',
    brdTitle: null,
    brdMeta: { problemTypeHint: null, complexity: null, sectionCount: null },
    nodes,
    revisionCount: 0,
    error: null,
  }
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

type Action =
  | { type: 'RESET' }
  | { type: 'EVENT'; event: PipelineEvent }

function deriveNodeStatuses(
  nodes: Record<NodeName, NodeState>,
  phase: PipelineState['phase'],
): Record<NodeName, NodeState> {
  if (phase !== 'running') return nodes

  // Find the last completed node index to mark the next one as 'running'
  let lastCompleteIdx = -1
  for (let i = 0; i < NODE_ORDER.length; i++) {
    const n = NODE_ORDER[i]
    if (nodes[n].status === 'complete' || nodes[n].status === 'stub') {
      lastCompleteIdx = i
    }
  }

  const next = lastCompleteIdx + 1
  if (next < NODE_ORDER.length) {
    const nextNode = NODE_ORDER[next]
    if (nodes[nextNode].status === 'pending') {
      return {
        ...nodes,
        [nextNode]: { ...nodes[nextNode], status: 'running' },
      }
    }
  }
  return nodes
}

function reducer(state: PipelineState, action: Action): PipelineState {
  if (action.type === 'RESET') return makeInitialState()

  const { event } = action

  switch (event.type) {
    case 'pipeline_start': {
      const nodes = makeInitialState().nodes
      // Mark first node as running immediately
      nodes['ingest'] = { ...nodes['ingest'], status: 'running' }
      return {
        ...makeInitialState(),
        phase: 'running',
        brdTitle: event.brd_title,
        brdMeta: {
          problemTypeHint: event.problem_type_hint,
          complexity: event.complexity,
          sectionCount: event.section_count,
        },
        nodes,
      }
    }

    case 'node_complete': {
      const eventNodeIdx = NODE_ORDER.indexOf(event.node)

      // Clear any 'running' node at a lower index — it was a conditional that was bypassed.
      // Without this, poc_planner stays spinning after tech_stack_recommender when it is skipped.
      const base = { ...state.nodes }
      for (let i = 0; i < eventNodeIdx; i++) {
        const n = NODE_ORDER[i]
        if (base[n].status === 'running') {
          base[n] = { ...base[n], status: 'pending' }
        }
      }

      const updatedNodes: Record<NodeName, NodeState> = {
        ...base,
        [event.node]: {
          status: event.is_stub ? 'stub' : 'complete',
          isStub: event.is_stub,
          output: event.output as Record<string, unknown>,
          completedAt: event.timestamp,
          revisionCount: event.revision_count,
          runCount: (base[event.node].runCount ?? 0) + 1,
        },
      }
      // Infer which node is now running
      const withRunning = deriveNodeStatuses(updatedNodes, 'running')
      return {
        ...state,
        nodes: withRunning,
        revisionCount: event.revision_count,
      }
    }

    case 'hitl_pending':
      return { ...state, phase: 'hitl_pending' }

    case 'pipeline_complete':
      return { ...state, phase: 'complete' }

    case 'pipeline_rejected':
      return { ...state, phase: 'rejected' }

    case 'error':
      return { ...state, phase: 'error', error: event.message }

    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const TERMINAL_TYPES = new Set(['pipeline_complete', 'pipeline_rejected', 'error'])

export function usePipelineStream(sessionId: string | null) {
  const [state, dispatch] = useReducer(reducer, undefined, makeInitialState)
  const esRef = useRef<EventSource | null>(null)
  // Tracks whether a terminal event was received so onerror doesn't
  // overwrite the real result when the server closes the connection.
  const terminatedRef = useRef(false)

  useEffect(() => {
    if (!sessionId) return

    dispatch({ type: 'RESET' })
    terminatedRef.current = false

    const es = new EventSource(`/api/stream/${sessionId}`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as PipelineEvent
        dispatch({ type: 'EVENT', event })

        // Close proactively on terminal events — prevents onerror from
        // firing when the server subsequently closes the connection.
        if (TERMINAL_TYPES.has(event.type)) {
          terminatedRef.current = true
          es.close()
        }
      } catch {
        // malformed event — ignore
      }
    }

    es.onerror = () => {
      // Suppress connection-close errors that arrive after a clean
      // pipeline_complete or explicit error event from the server.
      if (!terminatedRef.current) {
        dispatch({
          type: 'EVENT',
          event: {
            type: 'error',
            message: 'Lost connection to server',
            timestamp: new Date().toISOString(),
          },
        })
      }
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [sessionId])

  return state
}
