import { X, Shield, Zap, BarChart3, FileText, Cloud, Users } from 'lucide-react'

interface Props {
  onClose: () => void
}

const PRODUCTS = [
  {
    icon: Zap,
    name: 'ScoreIQ',
    desc: 'Async application fraud scoring API. Accepts an application payload, pulls bureau data from Experian / Equifax / TransUnion, runs ML inference, and delivers a score + reason codes to the lender webhook within 3 seconds.',
  },
  {
    icon: Shield,
    name: 'IdentityGraph',
    desc: 'Synthetic identity detection pipeline. Detects fabricated and manipulated identities by analysing credit file age, authorised user patterns, consortium velocity, and cross-bureau identity field consistency.',
  },
  {
    icon: FileText,
    name: 'ReasonIQ',
    desc: 'FCRA-compliant adverse action reason code engine. Maps SHAP feature importances to a versioned catalogue of 40+ human-readable reason codes. Guarantees exactly 4 codes per adverse-action decision.',
  },
  {
    icon: BarChart3,
    name: 'CaseTrack',
    desc: 'Analyst workbench for first-party fraud investigation. Includes SAR narrative drafting and FinCEN BSA E-Filing support. Case dispositions feed back into the model retraining pipeline.',
  },
]

const STACK = [
  { label: 'Cloud', value: 'AWS (us-east-1 primary · us-west-2 DR)' },
  { label: 'Compute', value: 'EKS (Graviton) · SageMaker (training / batch transform)' },
  { label: 'Async queue', value: 'Amazon SQS + SNS · AWS Step Functions' },
  { label: 'Features', value: 'Snowflake + dbt (nightly snapshots · no Tecton)' },
  { label: 'Databases', value: 'Aurora PostgreSQL · DynamoDB · ElastiCache Redis' },
  { label: 'ML', value: 'XGBoost · LightGBM · SHAP TreeExplainer · MLflow' },
  { label: 'API', value: 'FastAPI (Python 3.12) · Auth0 + JWT' },
  { label: 'Observability', value: 'Datadog · PagerDuty · Evidently AI · LangSmith' },
]

const CUSTOMERS = [
  { label: 'Lending platforms', desc: 'Consumer and small-business loan originators, BNPL providers, and personal credit marketplaces — first-party fraud and synthetic identity detection at origination' },
]

export default function AboutModal({ onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
              <Shield size={16} className="text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">Arbor Risk</h2>
              <p className="text-xs text-gray-400 mt-0.5">Fraud detection & risk decisioning · New York, NY</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors mt-0.5"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Mission */}
          <div>
            <p className="text-sm text-gray-600 leading-relaxed">
              Arbor Risk is a fraud detection and risk decisioning platform built exclusively for
              lending. We help consumer loan originators, BNPL providers, and personal credit
              marketplaces detect first-party fraud and synthetic identities at origination — before
              funds are disbursed. We operate our own in-house ML models on AWS, scoring applications
              asynchronously with bureau-integrated decisions delivered in under 3 seconds.
            </p>
          </div>

          {/* Customers */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">
              Customer segment
            </h3>
            <div className="space-y-2">
              {CUSTOMERS.map(({ label, desc }) => (
                <div key={label} className="flex items-start gap-3 bg-gray-50 rounded-xl px-4 py-3">
                  <Users size={13} className="text-indigo-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-gray-800">{label}</span>
                    <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Products */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">
              Products
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PRODUCTS.map(({ icon: Icon, name, desc }) => (
                <div key={name} className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon size={14} className="text-indigo-600 shrink-0" />
                    <span className="text-sm font-semibold text-gray-800">{name}</span>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Tech stack */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3 flex items-center gap-1.5">
              <Cloud size={12} />
              Current stack
            </h3>
            <div className="bg-gray-50 rounded-xl divide-y divide-gray-100">
              {STACK.map(({ label, value }) => (
                <div key={label} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="text-xs font-medium text-gray-400 w-32 shrink-0">{label}</span>
                  <span className="text-xs text-gray-700">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* About this tool */}
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <Shield size={13} className="text-indigo-600" />
              <span className="text-xs font-semibold text-indigo-800">About this tool</span>
            </div>
            <p className="text-xs text-indigo-700 leading-relaxed">
              This internal AI assistant converts Business Requirements Documents (BRDs) into
              decision-ready engineering plans using a multi-agent LangGraph pipeline. The Solution
              Architect produces 2-3 competing architectural options grounded in Arbor's RAG knowledge
              base — past ADRs, team skills, compliance constraints, and fraud domain context — so
              engineering managers can make informed build decisions faster.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
