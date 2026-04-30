import { useState } from 'react'
import { BookOpen, Box, CheckCircle2, GitMerge, Link, ShieldCheck, Shuffle, Star } from 'lucide-react'
import type { AgentOutput, ArchitectureDesign, ArchitectureOption } from '../types/pipeline'
import {
  COMPLEXITY_COLORS,
  PROBLEM_TYPE_COLORS,
  PROBLEM_TYPE_LABELS,
} from '../types/pipeline'

interface Props {
  output: AgentOutput
}

export default function SolutionArchitectCard({ output }: Props) {
  const design = output.content as ArchitectureDesign | undefined
  const [activeOptionId, setActiveOptionId] = useState<string>(
    design?.recommended_option_id ?? design?.options?.[0]?.option_id ?? 'A',
  )

  if (!design?.options?.length) return null

  const activeOption: ArchitectureOption | undefined = design.options?.find(
    (o) => o.option_id === activeOptionId,
  )

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Solution Architect</h3>
          <p className="text-xs text-gray-400 mt-0.5">Competing options · decision-ready design</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
              PROBLEM_TYPE_COLORS[design.problem_type] ?? 'bg-gray-100 text-gray-600 border-gray-200'
            }`}
          >
            {PROBLEM_TYPE_LABELS[design.problem_type] ?? design.problem_type}
          </span>
          {output.tokens_used && (
            <span className="text-xs text-gray-400">{output.tokens_used.toLocaleString()} tokens</span>
          )}
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* Classification rationale */}
        {design.classification_rationale && (
          <div className="text-xs text-gray-500 italic border-l-2 border-gray-200 pl-3">
            {design.classification_rationale}
          </div>
        )}

        {/* Recommendation banner */}
        {(design.recommended_option_id || design.recommendation_rationale) && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <Star size={13} className="text-emerald-600 fill-emerald-600" />
              <span className="text-xs font-semibold text-emerald-800">
                {design.recommended_option_id
                  ? `Recommended: Option ${design.recommended_option_id}${design.options?.find((o) => o.option_id === design.recommended_option_id)?.name ? ` — ${design.options.find((o) => o.option_id === design.recommended_option_id)!.name}` : ''}`
                  : 'Recommended option'}
              </span>
            </div>
            <p className="text-xs text-emerald-700 leading-relaxed">{design.recommendation_rationale}</p>
          </div>
        )}

        {/* Option tabs */}
        {design.options && design.options.length > 0 && (
          <div>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit mb-4">
              {design.options.map((opt) => {
                const isRec = opt.option_id === design.recommended_option_id
                const isActive = opt.option_id === activeOptionId
                return (
                  <button
                    key={opt.option_id}
                    onClick={() => setActiveOptionId(opt.option_id)}
                    className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                      isActive
                        ? 'bg-white text-gray-800 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {isRec && <Star size={10} className="text-emerald-500 fill-emerald-500 shrink-0" />}
                    Option {opt.option_id}
                  </button>
                )
              })}
            </div>

            {/* Active option detail */}
            {activeOption && (
              <div className="space-y-5">
                {/* Option name + complexity */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{activeOption.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{activeOption.description}</p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full border shrink-0 ml-3 ${
                      COMPLEXITY_COLORS[activeOption.estimated_complexity] ??
                      'bg-gray-100 text-gray-600 border-gray-200'
                    }`}
                  >
                    {activeOption.estimated_complexity} complexity
                  </span>
                </div>

                {/* Components */}
                <Section icon={<Box size={13} className="text-emerald-500" />} title="Components">
                  <div className="flex flex-wrap gap-2 mt-2">
                    {activeOption.high_level_components.map((c, i) => (
                      <span
                        key={i}
                        className="text-xs bg-gray-50 border border-gray-200 text-gray-700 px-3 py-1.5 rounded-full"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </Section>

                {/* Data flow */}
                <Section icon={<GitMerge size={13} className="text-emerald-500" />} title="Data flow">
                  <p className="mt-2 text-sm text-gray-600 leading-relaxed bg-gray-50 rounded-lg p-4 border border-gray-100">
                    {activeOption.data_flow}
                  </p>
                </Section>

                {/* Integration points */}
                <Section icon={<Link size={13} className="text-emerald-500" />} title="Integration points">
                  <ul className="mt-2 space-y-1.5">
                    {activeOption.integration_points.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                        {p}
                      </li>
                    ))}
                  </ul>
                </Section>

                {/* Constraints addressed */}
                <Section icon={<ShieldCheck size={13} className="text-emerald-500" />} title="Constraints addressed">
                  <ul className="mt-2 space-y-1.5">
                    {activeOption.constraints_addressed.map((c, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                        <CheckCircle2 size={13} className="text-emerald-500 shrink-0 mt-0.5" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </Section>

                {/* Trade-offs */}
                <Section icon={<Shuffle size={13} className="text-amber-500" />} title="Trade-offs">
                  <p className="mt-2 text-sm text-gray-600 leading-relaxed bg-amber-50 rounded-lg p-4 border border-amber-100">
                    {activeOption.trade_offs}
                  </p>
                </Section>
              </div>
            )}
          </div>
        )}

        {/* RAG sources */}
        {output.rag_context && output.rag_context.retrieved_chunks.length > 0 && (
          <Section icon={<BookOpen size={13} className="text-gray-400" />} title="RAG context">
            <div className="mt-2 flex flex-wrap gap-1.5">
              {output.rag_context.sources.map((s, i) => (
                <span
                  key={i}
                  className="text-[11px] bg-gray-50 border border-gray-100 text-gray-400 px-2 py-0.5 rounded-full"
                >
                  {s}
                </span>
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</span>
      </div>
      {children}
    </div>
  )
}
