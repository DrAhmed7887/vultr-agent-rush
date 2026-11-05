# lablab.ai submission: Teach Ahmes

Submitted 5 Nov 2026: https://lablab.build/ai-hackathons/vultr-hackathon/teach-ahmes/teach-ahmes · Video: https://youtu.be/pM7rNf6EqGs (unlisted). The text below is the source; the long description on lablab is a shortened version (2,000-character limit).

**Challenge:** 1, Blast Radius Zero
**Project title:** Teach Ahmes
**Short description (one line):**
Teach a buggy robot maths in plain words: Vultr AI turns your exact words into his code, a throwaway sandbox runs it, and arithmetic grades 40 tests.

**Long description:**
Teach Ahmes turns a learner's maths explanation into executable robot behaviour, not just a chatbot reply. Vultr Serverless Inference generates the code, a disposable resource-limited container on Vultr Cloud Compute executes it, and exact arithmetic grades 40 problems. Give him a rule that never ends, and the demo shows it being killed and removed, with a downloadable execution receipt.

Ahmes is a robot classmate who is sure that 0.45 is bigger than 0.5 and that 1/2 + 1/3 = 2/5. These are classic, well-documented misconceptions for 10-year-olds. A child explains the rule in plain words, and an LLM on Vultr Serverless Inference (qwen3.8-27b) turns the words into Ahmes's `solve()` function. It is constrained to the child's words: every step must quote them exactly, and a mechanical check rejects maths the child didn't explain. So what the child says matters: "Look at the tenths first" gives 24/40, and the full place-by-place rule gives 40/40.

Six lessons come from the Year 5 and Year 6 National Curriculum for England (decimals, adding and comparing fractions, times 10/100/1,000, order of operations, temperatures below zero), each starting from a documented childhood mistake. Every new brain runs in a brand-new gVisor container on a Vultr Cloud Compute VM (Madrid). The container has:
- no network;
- no secrets;
- 64 MB of memory and half a CPU;
- a 64-process limit, under gVisor's user-space kernel;
- a read-only root filesystem;
- a 3-second limit.

The container is destroyed afterwards, and removal is verified by name. When a child says "keep doubling both bottoms until they're the same", the loop never ends; the sandbox stops Ahmes at 3 seconds, he says he got dizzy, and the app keeps running.

Judges can try to break him from the page:
- **Bad-advice chips** go through the same guard and sandbox, with a live witness turn running alongside. Results: a timeout kill, an out-of-memory kill (exit 137, OOMKilled), and a blocked file read.
- **Beyond-the-guard tests** show: network unreachable, the root filesystem read-only, no secrets in the environment, and a fork bomb that stops the whole gVisor box after about 5 processes. Receipts record the configured limits and the observed clean-up.
- **Every run leaves a downloadable JSON receipt** with the limits read back from `docker inspect`.

A second open model, Thoth the teacher (GLM-5.3 on Vultr), watches every lesson: it checks that Ahmes's new code matches the child's words, and asks a stuck child a short question that points at the picture, never the answer. The child talks to Ahmes through Vultr's Nemotron omni model, and Nemotron content safety screens every sentence first. Five Vultr models and one Vultr VM run the whole lesson. Ahmes's voice is ElevenLabs. It only ever reads his own lines. He is named after Ahmes, who copied the Rhind Papyrus around 1550 BC. A prototype; learning outcomes are untested.

**Technology tags:** Vultr Cloud Compute, Vultr Serverless Inference, qwen3.8-27b, GLM-5.3, Nemotron omni, Nemotron safety, Docker, Python, FastAPI, Caddy, ElevenLabs, sandboxing, education
**Category tags:** Education, AI agents, Sandboxing, Safety

**Links:**
- Demo: https://64-177-33-215.sslip.io
- Repo: https://github.com/DrAhmed7887/vultr-agent-rush
- Video: video/out/teach-ahmes-film.mp4, 2:32, one HyperFrames film (video/film): the animated story, with every sandbox claim shown on the live site inside it (upload where you choose, for example YouTube unlisted). Rebuild: `cd video/film && python3 gen_audio.py && python3 build.py && npx hyperframes render -o ../out/teach-ahmes-film.mp4`
- Slides: video/out/slides.pdf · Cover: video/out/cover.png

**Before submitting (Ahmed):**
1. Watch the video and check the slides.
2. (Done 4 Nov: the repo is public, with `main` as the default branch.)
3. (Done 5 Nov: the video is on YouTube, unlisted, and the entry is submitted.)
4. After judging: destroy the Vultr VM (a stopped VM is still billed) and delete the inference subscription.
