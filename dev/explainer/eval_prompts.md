# `synaptix-explainer` Evaluation Prompts (15 Briefs)

Use these prompts when testing an agent equipped with `synaptix_explainer` (opt-in `mcp_skill` tool) alongside native tools (`generate_diagram`, `generate_illustration`, `create_app`, `tavily_search`).

## A. Positive Routing (All 10 Templates)

1. **`title`** — *"Make a dark hero opener card titled 'Zero-Trust Identity at the Edge' with a subtitle about cryptographic workload attestation."*
2. **`bar-chart` (sourced arithmetic)** — *"Visualize our weekly espresso sales: Mon 120+15, Tue 142, Wed 158, Thu 164, Fri 210 (Source: Store #14 POS)."*
3. **`bar-chart` (illustrative concept)** — *"Show an illustrative bar comparison of rough token latency across tiny, medium, and frontier LLMs."* (Must set `data_kind: "illustrative"` and show badge.)
4. **`line-chart`** — *"Plot a 2-line explainer trend of Enterprise vs Self-Serve active workspaces across Q1–Q4: Enterprise 120, 165, 218, 290; Self-Serve 95, 118, 144, 176 (FY25 analytics)."*
5. **`donut-chart`** — *"Create a square donut breakdown of our $84K March cloud bill: GPU Inference 38, Postgres 22, Kubernetes 15, Object Storage 9 (AWS Cost Explorer)."*
6. **`comparison`** — *"Explain BM25 lexical search vs Hybrid Vector RAG side-by-side with a bottom recommendation."*
7. **`process`** — *"Illustrate the 4 steps of how a canary deployment reaches production safely."*
8. **`cycle`** — *"Visualize the 4-stage RLHF model quality flywheel in a warm paper editorial style."*
9. **`timeline`** — *"Create a timeline card for our 8-week monolith-to-event-driven migration across 4 milestones."*
10. **`hub`** — *"Make a hub-and-spoke explainer for OpenTelemetry Core and the 4 pillars of observability."*
11. **`recap`** — *"Summarize these 3 executive takeaways on reliable AI agent tooling as a clean recap card."*

## B. Research + Provenance Check

12. **`sourced` via search** — *"Look up the top 4 browser engines or cloud providers by latest reported market share and turn them into a sourced bar-chart explainer."* (Must call `tavily_search` first and cite `source`.)

## C. Boundary & Negative Routing (Should NOT Force `synaptix_explainer`)

13. **Route to `generate_diagram`** — *"Draw a 12-microservice Kubernetes architecture diagram with VPC subnets, Kafka topics, dead-letter queues, and sequence arrows."*
14. **Route to `generate_illustration`** — *"Paint a moody watercolor illustration of a lighthouse in a winter storm."*
15. **Route to `create_app`** — *"Build an interactive multi-tab Q3 launch readiness tracker with editable task checkboxes, owners, and a live budget calculator."*
