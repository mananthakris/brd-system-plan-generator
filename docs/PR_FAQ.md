# PR/FAQ — PlanForge: AI-Powered Engineering Plan Generator

---

## Press Release

**FOR IMMEDIATE RELEASE**

### Arbor Risk Launches PlanForge, Turning Business Requirements into Decision-Ready Engineering Plans in Minutes

*Multi-agent AI system produces competing architectural options, scores plan quality, and routes for engineering manager approval — replacing days of senior engineering effort with a repeatable, auditable workflow*

**SAN FRANCISCO, CA** — Arbor Risk today announced PlanForge, an AI-powered engineering planning system that ingests Business Requirements Documents (BRDs, PRDs, or RFCs) and produces structured, decision-ready engineering plans complete with competing architectural options, technology stack recommendations, phased project timelines, and a quality score before any human reviews them.

Engineering teams spend 3–5 days per feature translating business requirements into technical plans detailed enough for an engineer to act on. Senior engineers and engineering managers shoulder most of this work — writing architecture documents, identifying trade-offs, estimating timelines, and validating that plans are internally consistent. This creates a bottleneck: planning throughput is constrained by the availability of your most expensive, most in-demand people.

PlanForge changes this. A team uploads a BRD. Within minutes, a pipeline of specialized AI agents produces: a multi-phase implementation plan with verifiable deliverables, two to three competing architectural options grounded in the company's actual tech stack and past architectural decisions, a technology stack recommendation with explicit trade-offs, and a Critic score across five quality dimensions — completeness, feasibility, specificity, consistency, and scope fit. If the plan doesn't meet the quality threshold, the system automatically revises it before a human ever sees it. When it does pass, the engineering manager receives a structured output ready for review and approval.

"We built PlanForge because the planning bottleneck was real and it was ours to solve," said the Arbor Risk engineering team. "Senior engineers were spending the first week of every feature cycle writing documents instead of writing code. PlanForge doesn't replace engineering judgment — it handles the first draft so that judgment can go where it matters: reviewing options, catching blind spots, and making the call."

PlanForge connects to a company's existing knowledge base — architecture decisions, current stack, team skills, and compliance standards — through a RAG pipeline, so every plan it produces is grounded in the constraints that are actually true for that team. The system is evaluated continuously against a suite of golden BRDs, and every prompt change ships only after a measurable score improvement is confirmed. Planning quality is treated like software quality: versioned, tested, and observable.

Teams can upload BRDs through a web UI or API. Plans are available within minutes. Every run is traced end-to-end in Arize Phoenix for observability, and every approval decision is logged with a full audit trail.

To get started, visit [arborrisk.com/planforge] or contact your Arbor Risk account team.

---

## Frequently Asked Questions

### External FAQs

**Q: What is PlanForge and who is it for?**

PlanForge is an AI-powered engineering planning system for engineering managers and technical leads at software companies. It is for teams that regularly convert business requirements into engineering plans and find that process slow, inconsistent, or dependent on a small number of senior people. It is not a replacement for engineering judgment — it is a first-draft generator that handles the rote structuring work so that human review is focused on decisions rather than document creation.

---

**Q: What does PlanForge actually produce?**

For a given BRD, PlanForge produces:

- **Problem classification**: whether the work is greenfield, a new feature, a migration, an integration, a PoC, or an enhancement — with a cited rationale
- **Phased implementation plan**: 3–6 sequential phases, each with specific engineering objectives, verifiable deliverables (not generic labels), duration estimates, and dependency ordering
- **Competing architectural options**: 2–3 meaningfully different approaches — e.g. synchronous vs. asynchronous, managed service vs. self-hosted — with components named from your actual stack, data flow descriptions, and explicit trade-offs
- **Technology stack recommendation**: the recommended option with pros, cons, and effort estimates for each alternative, grounded in your existing services and team skill profile
- **Quality score**: a 5-dimension Critic score (completeness, feasibility, specificity, consistency, scope fit) with dimension-level feedback, so you know exactly what to push back on
- **Executive summary**: a business-readable summary for non-technical stakeholders

---

**Q: How long does it take?**

A typical BRD produces a complete plan in 3–6 minutes. If the Critic score falls below the configured threshold, the system automatically revises the plan and re-scores — up to two revision cycles — before routing to a human. The total wall-clock time including revisions is usually under 10 minutes.

---

**Q: How does PlanForge know about our tech stack and constraints?**

PlanForge uses retrieval-augmented generation (RAG). You seed a knowledge base with your company's architecture decision records, current stack documentation, team skills profile, cloud infrastructure specs, domain context, and compliance standards. Every agent retrieves relevant context from this knowledge base at runtime — it does not rely on the LLM's general training knowledge for company-specific facts. If your stack changes, you update one file and re-seed. The agents adapt automatically.

---

**Q: What file formats does it accept?**

PDF, DOCX, Markdown, and plain text. The ingestion pipeline parses the document, classifies sections (objective, functional requirements, non-functional requirements, constraints, risks, out-of-scope), and tags metadata before any planning agent sees the content.

---

**Q: Does a human review every plan before it's used?**

Yes. PlanForge includes a Human-in-the-Loop (HITL) gate as a required step in the pipeline. After the Critic scores the plan and it meets the quality threshold, the graph pauses and routes the output to an engineering manager for review and approval. The manager can approve and proceed, or reject with notes that feed back into a revision. Every approval decision — who, when, what was reviewed — is logged in an immutable audit trail.

---

**Q: How do we know the plans are actually good?**

PlanForge runs a continuous evaluation harness against four golden BRDs representing real fraud-domain features of increasing complexity. Every agent output is scored by three independent evaluators: a rule-based structural checker, a rule-based completeness checker, and an LLM-as-judge evaluator with an agent-specific rubric. Scores are versioned — every prompt change is tagged with the prompt version that produced it, and a comparison CLI shows before/after score deltas across all agents before any change ships. Planning quality is measurable and improving over time.

---

### Internal FAQs

**Q: Why build this rather than having engineers use ChatGPT directly?**

A general-purpose LLM produces generic plans. PlanForge produces plans grounded in your actual architectural decisions, current stack, team skills, and compliance constraints — because those are retrieved from your knowledge base at runtime, not hallucinated from training data. The multi-agent structure matters too: classification, planning, architecture, and stack recommendation are separated into focused agents with structured outputs, so failures are isolated and observable. A single ChatGPT prompt produces a document; PlanForge produces typed, validated, versioned artifacts that downstream tools and humans can reason about.

---

**Q: What happens when an agent produces a bad output — hallucinated components, wrong timeline, inconsistent stack?**

Three things catch this before a human sees it. First, output schema validation runs at every agent boundary — structured outputs are validated against Pydantic models and rejected if they don't conform. Second, the Critic agent scores the combined output of all upstream agents against a 5-dimension rubric with specific pass thresholds per dimension; if any dimension fails, the graph loops back to planning with targeted revision notes. Third, the HITL gate means a human reviews the plan before it is acted on. The eval harness measures how often each failure type occurs so we can target prompt improvements at the actual failure modes, not hypothetical ones.

---

**Q: How do we ensure quality doesn't drift as we ship prompt changes?**

Prompts are versioned artifacts in `prompts/registry.py` — not embedded in agent code. Every prompt has a semantic version and a one-line changelog. When a prompt changes, the version bumps. `run_experiments.py` saves a score snapshot tagged with the current prompt versions to `evals/results/`. `compare_experiments.py --latest` prints a before/after table showing per-agent score deltas and which version changed. A prompt change ships only if the target agent's scores improve with no regressions elsewhere. This is the same discipline as canary deploys, applied to prompt engineering.

---

**Q: What is the cost per plan?**

Approximately 15,000–25,000 tokens per pipeline run using the configured models (one orchestrator-tier model for judgment-heavy agents, one faster model for structured-output agents, one low-cost model for LLM-as-judge evals). At current model pricing, a full pipeline run including up to two revision cycles costs less than $0.15. The eval harness — four golden BRDs, all three evaluators — costs approximately $0.50 per full evaluation cycle.

---

**Q: What if the company's BRDs contain sensitive or proprietary information?**

The pipeline runs entirely within your infrastructure. The only external calls are to your configured LLM provider (OpenAI by default, configurable). BRD content is not sent to Arize Phoenix — only span metadata and agent-level input/output summaries are traced. For air-gapped deployments, the LLM provider can be replaced with a self-hosted model endpoint by changing the `ORCHESTRATOR_MODEL` and `AGENT_MODEL` config values.

---

**Q: Why does the system loop back to the Plan Generator when the Critic rejects a plan, rather than routing to the Solution Architect or another agent?**

The Critic's revision notes identify what is wrong with the plan, not what is wrong with the architecture. The Plan Generator is the most likely source of failures on completeness, scope fit, and specificity — the three most common failure dimensions. The revision notes are injected directly into the Plan Generator's prompt as a targeted instruction, so the next pass addresses the specific gaps rather than starting from scratch. The Solution Architect's output is held in state and reused unless the revision notes explicitly flag an architecture inconsistency, which the orchestrator's conditional edges detect separately.

---

**Q: What's the plan for extending this to teams with very different stacks or domains?**

The RAG knowledge base is the only company-specific component. Swapping in a new knowledge base — different stack documentation, different ADRs, different domain context — changes what every agent retrieves and therefore what every agent recommends. The agents themselves are domain-agnostic; the domain lives in the sources. Adding a new domain is: drop files into `rag/sources/`, run `rag.seed`, update the golden BRDs for the new domain, re-run evals to establish a baseline. No agent code changes required.

---

*PlanForge is an internal tool developed by the Arbor Risk engineering platform team.*
