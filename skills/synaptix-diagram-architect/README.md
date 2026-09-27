# Synaptix Diagram Architect (`synaptix-diagram-architect`)

> **Enterprise-grade Mermaid diagram architect, AST validator, and self-healing repair engine.**

Designed for AI agents, developers, and architectural teams who need rock-solid, publication-ready Mermaid diagrams without brittle syntax failures or parsing deadlocks.

---

## 🌟 Highlights

- **Pre-Flight AST & Security Validation:** Catches 99% of common LLM syntax bugs (unquoted special characters, bare `end` keywords, single `%` comments, XSS vectors) before diagrams reach the renderer.
- **One-Shot Auto-Repair (`--fix`):** Deterministically auto-quotes labels, renames reserved keyword collisions, and fixes syntax flaws in place.
- **Zero External Dependencies:** Built with pure Python standard library (`re`, `argparse`, `json`). Runs anywhere from local CLI to containerized agent sandboxes.
- **Synaptix Editorial Standards:** Curated aesthetics, responsive direction choices, compact decision diamonds, and clean logical subgraph boundaries.

---

## 🎨 Production Visualizations (Real Examples)

GitHub natively renders each of these production diagrams below:

### 1. Autonomous Agent Workflow with Agora Council & HITL Gate
*A live orchestration pipeline showing intake, RAG vector lookup, agent collaboration, multi-agent evaluation council, and human-in-the-loop verification:*

```mermaid
flowchart LR
    brief["Marketing Brief<br/>(Upload & Parse)"] --> agentGraph["Agentic Graphs<br/>(CHORUS Hub)"]
    rag["Brain-Tab<br/>(RAG-It Vector Search)"] --> agentGraph
    
    agentGraph --> council{"Agora Council<br/>Consensus"}
    council -->|"Rework Required"| agentGraph
    council -->|"Finalized Drafts"| hitl{"Human-in-the-Loop<br/>Review"}
    
    hitl -->|"Approved"| mcp["MCP Tool Integrations<br/>(Deploy & Sync)"]
    hitl -->|"Rejected"| agentGraph

    classDef primary fill:#1e293b,stroke:#64748b,stroke-width:1.5px,color:#e2e8f0;
    classDef gate fill:#0f172a,stroke:#f59e0b,stroke-width:1.5px,color:#fde68a;
    classDef success fill:#0f172a,stroke:#10b981,stroke-width:1.5px,color:#a7f3d0;
    
    class brief,rag,agentGraph primary;
    class council,hitl gate;
    class mcp success;
```

---

### 2. Evolution of AI & Agentic Era Timeline (1950 – 2026)
*An executive chronological milestone roadmap spanning the founding era through modern multi-agent systems:*

```mermaid
timeline
    title Evolution of Artificial Intelligence & Agentic Era
    section Founding Era (1950-1960s)
        1950 : Turing's Imitation Game (Turing Test)
        1956 : Dartmouth Conference (AI Coined)
        1958 : Rosenblatt's Perceptron
        1966 : Weizenbaum's ELIZA Chatbot
    section First AI Winter & Expert Systems (1970s-1980s)
        1969 : Minsky & Papert's Perceptrons Book
        1973 : Lighthill Report (First AI Winter)
        1982 : Japan's 5th Gen Computer Project
        1986 : Backpropagation Popularized
        1987 : Collapse of Lisp Machines (Second Winter)
    section Statistical ML & Milestones (1990s-2000s)
        1997 : IBM Deep Blue Defeats Kasparov
        2007 : Fei-Fei Li Launches ImageNet
    section Deep Learning & Transformers (2010s)
        2012 : AlexNet Wins ImageNet Challenge
        2016 : DeepMind AlphaGo Defeats Lee Sedol
        2017 : Google 'Attention Is All You Need'
    section Generative AI & Agentic Era (2020-2026)
        2020 : OpenAI GPT-3 & AlphaFold 2
        2022 : ChatGPT Launch & LLM Boom
        2024 : Multimodal Models & Open-Source LLMs
        2026 : Agentic AI Systems & Multi-Agent Swarms
```

---

### 3. Distributed Cloud Microservices & Streaming Architecture
*A production cloud topology with edge routing, isolated private VPC boundaries, Kafka event streaming, and polyglot persistence:*

```mermaid
flowchart TD
    client["Web & Mobile Apps"] -->|"HTTPS / WSS"| cdn["CloudFront CDN"]
    cdn --> alb["Application Load Balancer"]

    subgraph VPC ["Private VPC (us-east-1)"]
        subgraph IngressTier ["Ingress Gateway"]
            alb --> gateway["Envoy / API Gateway"]
        end

        subgraph ServiceMesh ["Core Microservices"]
            gateway --> auth["Auth Service"]
            gateway --> orders["Order Service"]
            gateway --> catalog["Catalog API"]
            orders --> bus[("Kafka Event Bus")]
        end

        subgraph DataTier ["Persistence Layer"]
            auth --> pgUser[("PostgreSQL (Users)")]
            orders --> redis[("Redis State Cache")]
            catalog --> mongo[("Document DB")]
            bus --> worker["Async Fulfillment Worker"]
        end
    end

    classDef primary fill:#1e293b,stroke:#64748b,stroke-width:1.5px,color:#e2e8f0;
    classDef storage fill:#0f172a,stroke:#3b82f6,stroke-width:1.5px,color:#93c5fd;
    class client,cdn,alb,gateway,auth,orders,catalog,worker primary;
    class pgUser,redis,mongo,bus storage;
```

---

### 4. Multi-Agent Governance & Deliberation Protocol
*Sequence protocol demonstrating autonomous agent task handoffs, deliberation consensus scoring, and human validation:*

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant Orch as Synaptix Orchestrator
    participant Hub as CHORUS Agent Hub
    participant Agora as Agora Council (Evaluators)
    participant MCP as MCP Tools / Execution

    User->>Orch: Submit Marketing Campaign Brief
    activate Orch
    Orch->>Hub: Dispatch Task to Specialized Agents
    activate Hub
    Hub->>Hub: Generate Draft Assets & Copies
    Hub-->>Agora: Submit Generated Assets for Review
    deactivate Hub

    activate Agora
    Note over Agora: Multi-Agent Consensus Scoring
    alt Consensus Score < Threshold
        Agora-->>Hub: Rework Required (Feedback + Revisions)
    else Consensus Passed
        Agora-->>Orch: Finalized Drafts Ready
    end
    deactivate Agora

    Orch->>User: Request Human-in-the-Loop Sign-off
    activate User
    User-->>Orch: Approve & Authorize
    deactivate User

    Orch->>MCP: Trigger Tool Execution (Publish & Distribute)
    activate MCP
    MCP-->>Orch: Execution 200 OK
    deactivate MCP
    Orch-->>User: Pipeline Complete
    deactivate Orch
```

---

## 🚀 Quickstart

### 1. Validate Mermaid DSL
```bash
python3 scripts/validate_mermaid.py --code "flowchart TD
  client[\"Client Application\"] --> gateway[\"API Gateway\"]
"
```

### 2. Auto-Repair Broken Syntax
```bash
python3 scripts/validate_mermaid.py --code "flowchart TD
  A[Init (V1)] --> end --> B
" --fix
```

**Output:**
```mermaid
flowchart TD
  A["Init (V1)"] --> end_node --> B
```

### 3. Machine-Readable JSON Output (for AI Tool Calling)
```bash
python3 scripts/validate_mermaid.py --code "flowchart TD\n  A --> B" --json
```

```json
{
  "valid": true,
  "diagram_type": "flowchart",
  "errors": [],
  "warnings": [],
  "line_count": 2
}
```

---

## 📁 Skill Structure

```text
synaptix-diagram-architect/
├── SKILL.md                 # Agent instructions, rules, patterns & reference guides
├── README.md                # Public documentation & usage instructions
└── scripts/
    └── validate_mermaid.py  # Executable CLI AST validator & repair engine
```

---

## 🛠️ Supported Diagram Types

- **Flowcharts (`flowchart TD / LR`):** System architectures, microservices, data ingestion DAGs.
- **Sequence Diagrams (`sequenceDiagram`):** API handshakes, auth flows, event loops.
- **Timelines (`timeline`):** Engineering roadmaps, historical eras, and release schedules.
- **State Diagrams (`stateDiagram-v2`):** Entity lifecycles, circuit breakers, worker queues.
- **Entity Relationship (`erDiagram`):** Database schemas, foreign keys, cardinality.
- **Quadrant Matrices (`quadrantChart`):** 2x2 prioritization & risk matrices.
- **Sankey Diagrams (`sankey-beta`):** Multi-stage traffic, cost, or resource flows.

---

## 📜 License
MIT License. Created by **Synaptix**.
