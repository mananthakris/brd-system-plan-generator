import { useState } from 'react'
import AboutModal from './components/AboutModal'
import BRDInput from './components/BRDInput'
import OutputPanel from './components/OutputPanel'
import PipelineStatus from './components/PipelineStatus'
import { usePipelineStream } from './hooks/usePipelineStream'

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [showAbout, setShowAbout] = useState(false)

  const pipeline = usePipelineStream(sessionId)
  const isRunning = pipeline.phase === 'running' || pipeline.phase === 'hitl_pending'

  // Clear isStarting once the pipeline transitions away from idle
  if (isStarting && pipeline.phase !== 'idle') {
    setIsStarting(false)
  }

  async function handleRun(
    title: string,
    payload: { text: string } | { file: File },
  ) {
    setSubmitError(null)
    setIsStarting(true)

    const form = new FormData()
    form.append('title', title)
    if ('text' in payload) {
      form.append('brd_text', payload.text)
    } else {
      form.append('brd_file', payload.file)
    }

    try {
      const res = await fetch('/api/run', { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${res.status}`)
      }
      const { session_id } = await res.json()
      setSessionId(session_id)
    } catch (err) {
      setIsStarting(false)
      setSubmitError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 bg-indigo-600 rounded flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 1.5L2 4.5V9.5L7 12.5L12 9.5V4.5L7 1.5Z" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="7" cy="7" r="1.5" fill="white"/>
            </svg>
          </div>
          <div>
            <span className="text-sm font-semibold text-gray-800">Arbor Risk</span>
            <span className="mx-2 text-gray-300">·</span>
            <span className="text-sm text-gray-400">BRD → Engineering Plan</span>
          </div>
        </div>
        <button
          onClick={() => setShowAbout(true)}
          className="text-xs text-gray-400 hover:text-indigo-600 font-medium transition-colors"
        >
          About
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: pipeline status */}
        <PipelineStatus pipeline={pipeline} isStarting={isStarting} />

        {/* Right: main content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Input form — always visible; disabled while running */}
          <BRDInput onRun={handleRun} isRunning={isRunning || isStarting} />

          {submitError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-600">
              {submitError}
            </div>
          )}

          {/* Output — only shown after a run starts */}
          {sessionId && <OutputPanel pipeline={pipeline} sessionId={sessionId} />}
        </main>
      </div>
    </div>
  )
}
