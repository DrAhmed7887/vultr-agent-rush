# lablab.ai submission: Teach Ahmes (draft for Ahmed to review and paste)

**Challenge:** 1, Blast Radius Zero
**Project title:** Teach Ahmes
**Short description (one line):**
A child teaches a robot classmate fractions; her words are compiled literally into his code, run in a throwaway Vultr sandbox, and checked by exact arithmetic.

**Long description:**
Ahmes is a robot classmate who is sure that 0.45 is bigger than 0.5 and that 1/2 + 1/3 = 2/5. These are classic, well-documented misconceptions for 10-year-olds. A child explains the rule in plain words, and an LLM on Vultr Serverless Inference (qwen3.8-27b) compiles the words *literally* into Ahmes's `solve()` function. Every step must quote the child exactly, and a mechanical quote check rejects any maths the child didn't say. That's why the teaching is real: "Look at the tenths first" gives 24/40, and the full place-by-place rule gives 40/40.

Every new brain runs in a brand-new container on a Vultr Cloud Compute VM (Madrid). The container has:
- no network;
- no secrets;
- 64 MB of memory and half a CPU;
- 32 processes;
- a read-only disk;
- a 3-second limit.

The container is destroyed afterwards, and removal is verified by name. When a child says "keep doubling both bottoms until they're the same", the loop never ends; the sandbox stops Ahmes at 3 seconds, he says he got dizzy, and the app keeps running.

Judges can try to break him from the page:
- **Bad-advice chips** go through the same guard and sandbox, with a live witness turn running alongside. Results: a timeout kill, an out-of-memory kill (exit 137, OOMKilled), and a blocked file read.
- **Beyond-the-guard tests** show: network unreachable, a read-only disk, no secrets visible, and a fork bomb capped at 30 processes.
- **Every run leaves a downloadable JSON receipt** with the limits read back from `docker inspect`.

Ahmes's voice is ElevenLabs. It only ever reads his own lines. He is named after the Egyptian scribe of the Rhind Papyrus (about 1550 BC), the oldest surviving maths book with fractions. A prototype; learning outcomes are untested.

**Technology tags:** Vultr Cloud Compute, Vultr Serverless Inference, qwen3.8-27b, Docker, Python, FastAPI, Caddy, ElevenLabs, sandboxing, education
**Category tags:** Education, AI agents, Sandboxing, Safety

**Links:**
- Demo: https://64-177-33-215.sslip.io
- Repo: https://github.com/DrAhmed7887/vultr-agent-rush (currently PRIVATE; make it public before submitting)
- Video: video/out/teach-ahmes-demo.mp4 (upload where you choose, for example YouTube unlisted)
- Slides: video/out/slides.pdf · Cover: video/out/cover.png

**Before submitting (Ahmed):**
1. Watch the video and check the slides.
2. Make the GitHub repo public, and merge the branch `spec/teach-ahmes` into `main`.
3. Upload the video, then fill in the lablab form with the text above. Deadline: Sun 8 Nov, 22:00 UTC (23:00 CET).
4. After judging: destroy the Vultr VM (a stopped VM is still billed) and delete the inference subscription.
