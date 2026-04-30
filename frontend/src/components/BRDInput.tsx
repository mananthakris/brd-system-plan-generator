import { FileText, Play, Upload, X } from 'lucide-react'
import { useRef, useState } from 'react'

interface Props {
  onRun: (title: string, payload: { text: string } | { file: File }) => void
  isRunning: boolean
}

export default function BRDInput({ onRun, isRunning }: Props) {
  const [title, setTitle] = useState('')
  const [mode, setMode] = useState<'text' | 'file'>('text')
  const [brdText, setBrdText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canRun = !isRunning && title.trim() && (mode === 'text' ? brdText.trim() : !!file)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canRun) return
    if (mode === 'text') {
      onRun(title.trim(), { text: brdText.trim() })
    } else if (file) {
      onRun(title.trim(), { file })
    }
  }

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">BRD / PRD Input</h2>

      {/* Title */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-500 mb-1">Document title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Real-Time Transaction Scoring Engine"
          disabled={isRunning}
          className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-50 disabled:bg-gray-50"
        />
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 mb-3 bg-gray-100 p-1 rounded-lg w-fit">
        {(['text', 'file'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            disabled={isRunning}
            className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
              mode === m
                ? 'bg-white text-gray-800 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {m === 'text' ? 'Paste text' : 'Upload file'}
          </button>
        ))}
      </div>

      {/* Text input */}
      {mode === 'text' && (
        <div className="mb-4">
          <textarea
            value={brdText}
            onChange={(e) => setBrdText(e.target.value)}
            disabled={isRunning}
            placeholder="Paste your BRD, PRD, or RFC here…"
            rows={10}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-400 resize-y disabled:opacity-50 disabled:bg-gray-50"
          />
        </div>
      )}

      {/* File upload */}
      {mode === 'file' && (
        <div
          className="mb-4 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center cursor-pointer hover:border-emerald-300 transition-colors"
          onClick={() => !isRunning && fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.md,.txt"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <div className="flex items-center justify-center gap-2">
              <FileText size={16} className="text-emerald-500" />
              <span className="text-sm text-gray-700 font-medium">{file.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setFile(null) }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <Upload size={20} />
              <span className="text-sm">Drop a file or click to browse</span>
              <span className="text-xs">.pdf · .docx · .md · .txt</span>
            </div>
          )}
        </div>
      )}

      <button
        type="submit"
        disabled={!canRun}
        className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
      >
        <Play size={14} />
        {isRunning ? 'Running…' : 'Run pipeline'}
      </button>
    </form>
  )
}
