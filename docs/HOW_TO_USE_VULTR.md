# How to Use Vultr for Agent Rush (Blast Radius Zero)

This guide details how to spend your $200 credits, configure Vultr Serverless Inference, and deploy the sandboxed agent runtime.

---

## 1. Using Vultr Serverless Inference

Vultr Serverless Inference provides an OpenAI-compatible API at `https://api.vultrinference.com/v1`. You do not need to configure GPUs—Vultr hosts the models on high-performance infrastructure with pay-per-token or credit consumption.

### A. Python Example (OpenAI SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("VULTR_INFERENCE_API_KEY"),
    base_url="https://api.vultrinference.com/v1"
)

response = client.chat.completions.create(
    model="meta/llama-3.3-70b-instruct",
    messages=[
        {"role": "system", "content": "You are an autonomous planner. Produce deterministic executable steps."},
        {"role": "user", "content": "Plan a sandboxed Python data extraction task."}
    ],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

### B. TypeScript / Node Example

```typescript
import OpenAI from "openai";

const vultr = new OpenAI({
  apiKey: process.env.VULTR_INFERENCE_API_KEY,
  baseURL: "https://api.vultrinference.com/v1",
});

const completion = await vultr.chat.completions.create({
  model: "meta/llama-3.3-70b-instruct",
  messages: [{ role: "user", content: "Analyze system logs securely." }],
});
```

---

## 2. Deploying the Backend on Vultr Cloud Compute

1. **Spin up a Cloud Compute VM**:
   * OS: Ubuntu 24.04 LTS
   * Plan: Regular Performance (2 vCPU, 4GB RAM is ~$20/month, comfortably within the $200 budget)
   * Region: Silicon Valley, Frankfurt, or New Jersey
2. **Install Docker & Containment Tools**:
   ```bash
   sudo apt update && sudo apt install -y docker.io git curl
   sudo systemctl enable --now docker
   ```
3. **Run Sandboxed Execution (Pattern A - Code Execution)**:
   * Spawn throwaway Docker containers with restricted capabilities:
   ```bash
   docker run --rm \
     --network none \
     --memory 512m \
     --cpus 1.0 \
     --pids-limit 100 \
     python:3.11-slim python -c "print('Executing inside isolated sandbox')"
   ```
4. **Run Sandboxed Execution (Pattern B - Browser Automation)**:
   * Spawn headless Chromium / Playwright container to perform user-requested web actions.
   * Pipe back screenshots and action traces to the verifier before executing irreversible actions.

---

## 3. Challenge 1 Judging Requirement: "Containment Moment"

The hackathon rules explicitly state:
> *"Challenge 1: Demonstrate at least one containment moment in your demo video, as described in the challenge brief."*

### How to demonstrate containment:
1. The agent plans a multi-step task.
2. A malicious or rogue payload tries to access `/etc/passwd`, probe the host network, or consume unbounded memory/CPU.
3. The Vultr sandbox catches the violation:
   * Network blocked: egress blocked by `--network none` or proxy firewall.
   * Resource limit enforced: OOM killer triggers within 512MB threshold.
   * File boundary enforced: container filesystem wiped on exit.
4. The central control layer logs the containment event with verifiable proof and continues safely.
