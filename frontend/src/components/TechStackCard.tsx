import { useState } from 'react'
import { Layers, CheckCircle2, XCircle, Star } from 'lucide-react'
import type { AgentOutput, TechStackRecommendation, TechOption } from '../types/pipeline'

interface Props {
  output: AgentOutput
}

export default function TechStackCard({ output }: Props) {
  const rec = output.content as TechStackRecommendation
  if (!rec?.options?.length) return null

  const [activeOption, setActiveOption] = useState<string>(rec.recommended ?? rec.options[0]?.name)
  const current = rec.options.find((o) => o.name === activeOption) ?? rec.options[0]

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 bg-indigo-100 rounded-md flex items-center justify-center">
            <Layers size={13} className="text-indigo-600" />
          </div>
          <span className="text-sm font-semibold text-gray-800">Tech Stack</span>
        </div>
        <span className="text-xs text-gray-400">{rec.options.length} options</span>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Recommendation banner */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Star size={12} className="text-indigo-500 fill-indigo-500" />
            <span className="text-xs font-semibold text-indigo-800">
              Recommended: {rec.recommended}
            </span>
          </div>
          <p className="text-xs text-indigo-700 leading-relaxed">{rec.rationale}</p>
        </div>

        {/* Option tabs */}
        <div className="flex gap-1.5 flex-wrap">
          {rec.options.map((opt) => {
            const isRec = opt.name === rec.recommended
            const isActive = opt.name === activeOption
            return (
              <button
                key={opt.name}
                onClick={() => setActiveOption(opt.name)}
                className={[
                  'text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300',
                ].join(' ')}
              >
                {isRec && !isActive && <Star size={9} className="inline mr-1 text-amber-400 fill-amber-400" />}
                {opt.name}
              </button>
            )
          })}
        </div>

        {/* Active option detail */}
        {current && <OptionDetail option={current} />}
      </div>
    </div>
  )
}

function OptionDetail({ option }: { option: TechOption }) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 space-y-3">
      <p className="text-xs text-gray-600 leading-relaxed">{option.rationale}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Pros */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600 mb-1.5">
            Advantages
          </p>
          <ul className="space-y-1">
            {option.pros.map((p, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                <CheckCircle2 size={11} className="text-emerald-500 shrink-0 mt-0.5" />
                {p}
              </li>
            ))}
          </ul>
        </div>

        {/* Cons */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-600 mb-1.5">
            Trade-offs
          </p>
          <ul className="space-y-1">
            {option.cons.map((c, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                <XCircle size={11} className="text-amber-500 shrink-0 mt-0.5" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="pt-1 border-t border-gray-100">
        <span className="text-xs text-gray-400">Estimated effort: </span>
        <span className="text-xs font-medium text-gray-700">{option.estimated_effort}</span>
      </div>
    </div>
  )
}
