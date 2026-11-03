# Vultr Agent Rush — Blast Radius Zero

> **Containment-first autonomous agent execution on Vultr Cloud infrastructure.**

Built for the **Vultr: Agent Rush Hackathon** on [lablab.ai](https://lablab.ai/ai-hackathons/vultr-hackathon) (3–8 November 2026).

---

## Challenge Track: Blast Radius Zero

An agent that only chats is a demo; an agent that executes safely is a product.

This project implements a centralized control layer that plans multi-step tasks, dispatches real work into an isolated execution sandbox on Vultr, and returns cryptographically verified, grounded output.

### Key Pillars
1. **Central Control Layer**: Orchestrates task planning, tool synthesis, and dispatch.
2. **Strict Sandboxing on Vultr**: Code and browser executions are strictly contained inside isolated sandbox environments running on Vultr Compute.
3. **Vultr Serverless Inference**: Powers model planning and reasoning via `https://api.vultrinference.com/v1`.
4. **Verifiable Containment**: Visual inspection and containment logs prove zero blast radius escape.

---

## Vultr Infrastructure Architecture
- **Compute**: Vultr Cloud Compute VM hosting the orchestration backend and sandbox runtime.
- **Inference**: Vultr Serverless Inference (OpenAI-compatible endpoints).
- **Containment**: Isolated containerized sandboxes with memory, process, and network limits.

---

## Quickstart

### Prerequisites
- Node.js 20+ / Python 3.11+
- Docker
- Vultr API Key & Serverless Inference Key

```bash
# Clone the repository
git clone https://github.com/DrAhmed7887/vultr-agent-rush.git
cd vultr-agent-rush

# Setup environment
cp .env.example .env
```

---

## License
MIT
