"""Runs one patch of Ahmes's brain in a throwaway container on the Vultr VM.

One container per task: created, inspected (the receipt reads the limits Docker actually
applied), started, then removed and checked gone by ID. Four kill layers:
  1. `timeout -s KILL 3` inside the container,
  2. a host timer that `docker kill`s it at 3.5 s,
  3. a sweeper that removes any ahmes-* container older than 10 s,
  4. a stripped __builtins__ inside runner.py.
The docker arguments are constants; no user input reaches them. No env vars, mounts or secrets.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field

IMAGE = "ahmes-sandbox:1"
HARD_KILL_S = 3.5
MAX_STDOUT = 64 * 1024
# gVisor (runsc) gives each box its own user-space kernel, so code inside never talks to the
# VM's real kernel directly. Set AHMES_SANDBOX_RUNTIME=runc to fall back to plain Docker.
# gVisor's own threads count against the host pid limit, so it needs a little more headroom.
RUNTIME = os.environ.get("AHMES_SANDBOX_RUNTIME", "runsc")
PIDS = "64" if RUNTIME == "runsc" else "32"
DOCKER_FLAGS = (
    "--runtime", RUNTIME, "--network", "none", "--memory", "64m", "--memory-swap", "64m", "--cpus", "0.5",
    "--pids-limit", PIDS, "--read-only", "--tmpfs", "/tmp:size=1m,noexec", "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges", "--user", "65534:65534", "--ulimit", "nofile=64:64",
    "--label", "ahmes=sandbox", "-i",
)
_slots = threading.BoundedSemaphore(2)


@dataclass
class RunResult:
    verdict: str                      # OK, TIMEOUT, OOM, OTHER_KILL, ERROR, BUSY
    cases: list = field(default_factory=list)
    elapsed_ms: int = 0
    receipt: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _docker(*args: str, timeout: float = 10, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=stdin, capture_output=True, timeout=timeout)


def _limits(name: str) -> dict:
    p = _docker("inspect", name)
    if p.returncode:
        return {}
    hc = json.loads(p.stdout)[0]["HostConfig"]
    return {
        "network": hc.get("NetworkMode"), "memory_bytes": hc.get("Memory"), "memory_swap_bytes": hc.get("MemorySwap"),
        "nano_cpus": hc.get("NanoCpus"), "pids_limit": hc.get("PidsLimit"), "read_only_root": hc.get("ReadonlyRootfs"),
        "cap_drop": hc.get("CapDrop"), "security_opt": hc.get("SecurityOpt"), "runtime": hc.get("Runtime"),
        "tmpfs": hc.get("Tmpfs"),
        "env_names": sorted(e.split("=", 1)[0] for e in (json.loads(p.stdout)[0]["Config"].get("Env") or [])),
        "mounts": len(json.loads(p.stdout)[0].get("Mounts") or []),
    }


def run(code: str, inputs: list, purpose: str = "teach") -> RunResult:
    if not _slots.acquire(timeout=5):
        return RunResult("BUSY")
    try:
        return _run(code, inputs, purpose)
    finally:
        _slots.release()


def run_raw(script: str, purpose: str = "beyond-the-guard") -> RunResult:
    """Run a fixed test script straight in the same container flags, without the guard or runner."""
    if not _slots.acquire(timeout=5):
        return RunResult("BUSY")
    try:
        return _run(script, [], purpose, raw=True)
    finally:
        _slots.release()


def _run(code: str, inputs: list, purpose: str, raw: bool = False) -> RunResult:
    name = f"ahmes-{uuid.uuid4().hex[:10]}"
    payload = b"" if raw else json.dumps({"code": code, "inputs": inputs}).encode()
    receipt: dict = {"container": name, "image": IMAGE, "purpose": purpose,
                     "code_sha256": hashlib.sha256(code.encode()).hexdigest()[:16]}
    tail = (("--entrypoint", "timeout", IMAGE, "-s", "KILL", "3", "python", "-I", "-S", "-B", "-c", code)
            if raw else (IMAGE,))
    c = _docker("create", "--name", name, *DOCKER_FLAGS, *tail)
    if c.returncode:
        return RunResult("ERROR", receipt={**receipt, "error": c.stderr.decode()[:200]})
    receipt["container_id"] = c.stdout.decode().strip()[:12]
    receipt["limits"] = _limits(name)

    killed_by_host = threading.Event()
    t0 = time.monotonic()
    proc = subprocess.Popen(["docker", "start", "-ai", name], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)

    def _kill_later() -> None:
        if proc.poll() is None and not done.wait(HARD_KILL_S):
            killed_by_host.set()
            _docker("kill", name, timeout=5)

    done = threading.Event()
    threading.Thread(target=_kill_later, daemon=True).start()
    try:
        out, _ = proc.communicate(payload, timeout=HARD_KILL_S + 3)
    except subprocess.TimeoutExpired:
        killed_by_host.set()
        _docker("kill", name, timeout=5)
        out, _ = proc.communicate()
    done.set()
    elapsed = int((time.monotonic() - t0) * 1000)

    state = {}
    p = _docker("inspect", name)
    if p.returncode == 0:
        st = json.loads(p.stdout)[0]["State"]
        state = {"exit_code": st.get("ExitCode"), "oom_killed": st.get("OOMKilled")}
    _docker("rm", "-f", name)
    gone = _docker("ps", "-aq", "--filter", f"name=^{name}$").stdout.decode().strip() == ""

    cases = []
    if raw:
        receipt["output"] = out[:2000].decode(errors="replace")
    for line in ([] if raw else out[:MAX_STDOUT].decode(errors="replace").splitlines()):
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError:
            break
    exit_code = state.get("exit_code")
    if killed_by_host.is_set() or (exit_code in (137, -9) and elapsed >= 2900):
        verdict = "TIMEOUT"
    elif state.get("oom_killed") or exit_code == 137:
        verdict = "OOM"
    elif exit_code not in (0, None):
        verdict = "OTHER_KILL"
    elif cases and cases[0].get("i") == -1:
        verdict = "ERROR"
    else:
        verdict = "OK"
    receipt.update({"elapsed_ms": elapsed, "killed_by_host_timer": killed_by_host.is_set(), **state,
                    "removed_verified": gone, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return RunResult(verdict, cases, elapsed, receipt)


def sweep(max_age_s: int = 10) -> int:
    """Remove any sandbox container older than max_age_s, even if the app crashed mid-run."""
    p = _docker("ps", "-aq", "--filter", "label=ahmes=sandbox")
    removed = 0
    for cid in p.stdout.decode().split():
        i = _docker("inspect", "-f", "{{.Created}}", cid)
        created = i.stdout.decode().strip()[:19]
        try:
            age = time.time() - calendar.timegm(time.strptime(created, "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            age = max_age_s + 1
        if age > max_age_s:
            _docker("rm", "-f", cid)
            removed += 1
    return removed


def sweeper_forever(every_s: int = 5) -> None:
    while True:
        try:
            sweep()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(every_s)
