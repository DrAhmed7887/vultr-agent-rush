"""Teach Ahmes: the orchestrator on the Vultr VM.

One teach turn: child's words -> literal compiler (Vultr Serverless Inference) -> quote check
-> AST guard -> throwaway container -> exact checker -> behaviour read-out -> Ahmes's reply
-> his voice (ElevenLabs). Children's sentences live only in memory and are purged after 24 h.
"""
from __future__ import annotations

import concurrent.futures as cf
import random
import secrets
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import classifier, compiler, fixtures, guard, replies, sandbox, voice
from .skills import SKILLS

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path("/var/lib/ahmes/runs.db") if Path("/var/lib/ahmes").exists() else ROOT / "runs.db"
SESSION_TTL_S = 24 * 3600
MAX_SENTENCE = 500

app = FastAPI(title="Teach Ahmes", docs_url=None, redoc_url=None)
_sessions: dict[str, dict] = {}
_lock = threading.Lock()
_rate: dict[str, deque] = {}
_pool = cf.ThreadPoolExecutor(max_workers=4)


# ---------- storage: the runs log holds receipts only, never a child's words ----------

def _db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, at REAL, purpose TEXT, verdict TEXT,"
                " elapsed_ms INTEGER, container TEXT, removed INTEGER, receipt TEXT)")
    return con


def _log_run(purpose: str, r: sandbox.RunResult) -> str:
    import json
    run_id = secrets.token_hex(6)
    with _db() as con:
        con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, time.time(), purpose, r.verdict, r.elapsed_ms, r.receipt.get("container", ""),
                     int(bool(r.receipt.get("removed_verified"))), json.dumps({**r.receipt, "verdict": r.verdict})))
    return run_id


# ---------- sessions ----------

def _session(sid: str) -> dict:
    now = time.time()
    with _lock:
        for k in [k for k, v in _sessions.items() if now - v["created"] > SESSION_TTL_S]:
            del _sessions[k]
        s = _sessions.get(sid)
        if s is None:
            raise HTTPException(404, "Session expired. Reload the page.")
        return s


def _limit(request: Request, per_min: int = 20, bucket: str = "teach") -> None:
    ip = request.client.host if request.client else "?"
    q = _rate.setdefault(f"{bucket}:{ip}", deque())
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= per_min:
        raise HTTPException(429, "Too many tries. Wait a minute.")
    q.append(now)


class NewSession(BaseModel):
    pass


class Teach(BaseModel):
    sid: str = Field(max_length=40)
    skill: str = Field(max_length=40)
    sentence: str = Field(max_length=MAX_SENTENCE)


class SkillReq(BaseModel):
    sid: str = Field(max_length=40)
    skill: str = Field(max_length=40)


class Chip(BaseModel):
    sid: str = Field(max_length=40)
    chip: str = Field(max_length=40)


def _skill(name: str):
    if name not in SKILLS:
        raise HTTPException(400, "Unknown skill")
    return SKILLS[name]


def _grade(sk, probs, run) -> dict:
    right, rows = 0, []
    by_i = {c.get("i"): c for c in run.cases}
    for i, p in enumerate(probs):
        c = by_i.get(i)
        status = c["status"] if c else ("dizzy" if run.verdict == "TIMEOUT" else "too_full" if run.verdict == "OOM" else "not_run")
        ok = bool(c) and status == "ok" and sk.grade(p, c["out"])
        right += ok
        rows.append({"problem": sk.show(p), "answer": sk.show_answer(p, c["out"]) if c and status == "ok" else status,
                     "ok": ok, "status": status})
    return {"right": right, "total": len(probs), "rows": rows}


def _check(sk, code: str, seed: int, purpose: str) -> tuple[dict, sandbox.RunResult, list]:
    probs = sk.problems(seed, 40)
    run = sandbox.run(code, [list(p) for p in probs], purpose)
    return _grade(sk, probs, run), run, probs


def _read_out(sk, code: str, seed: int, run: sandbox.RunResult, probs: list) -> dict:
    outs = {c["i"]: c.get("out") for c in run.cases if c.get("status") == "ok"}
    idx = [i for i in range(len(probs)) if i in outs]
    cls = classifier.classify(sk.name, [probs[i] for i in idx], [outs[i] for i in idx]) if idx else \
        {"behaves_like": "unknown", "label": "no answers to read", "matches": {}, "n": 0, "unknown": 1.0}
    # the next trap: a fresh problem where his current rule and the right rule disagree
    pool = sk.problems(seed + 997, 60)
    probe = classifier.next_probe(sk.name, cls["behaves_like"], pool)
    trap = None
    if probe is not None:
        pr = sandbox.run(code, [list(probe)], "probe")
        c = pr.cases[0] if pr.cases else {}
        trap = {"problem": sk.show(probe), "his_answer": sk.show_answer(probe, c.get("out")) if c.get("status") == "ok" else c.get("status", "?"),
                "args": list(probe), "out": c.get("out")}
    cls["trap"] = trap
    return cls


@app.post("/api/session")
def new_session(request: Request) -> dict:
    _limit(request, 30, "session")
    sid = secrets.token_urlsafe(12)
    with _lock:
        _sessions[sid] = {"created": time.time(), "seed": random.randrange(1, 10 ** 6),
                          "brains": {k: s.start_code for k, s in SKILLS.items()}, "history": {k: [] for k in SKILLS}}
    return {"sid": sid, "skills": {k: {"title": s.title, "code": s.start_code,
                                       "welcome": replies.FIXED[f"welcome_{k}"],
                                       "voice": voice.speak(replies.FIXED[f"welcome_{k}"])} for k, s in SKILLS.items()}}


@app.post("/api/teach")
def teach(t: Teach, request: Request) -> dict:
    _limit(request)
    s, sk = _session(t.sid), _skill(t.skill)
    sentence = " ".join(t.sentence.split())
    if not sentence:
        raise HTTPException(400, "Type what Ahmes should do.")
    current = s["brains"][sk.name]
    timeline = []
    t0 = time.monotonic()

    def mark(stage: str, **kw):
        timeline.append({"stage": stage, "ms": int((time.monotonic() - t0) * 1000), **kw})

    comp = compiler.compile_sentence(current, sentence)
    mark("compile", model=comp.model, ok=comp.ok, tokens=comp.usage.get("total_tokens"))
    if comp.no_rule:
        line = replies.FIXED["no_rule"]
        return {"outcome": "no_rule", "say": line, "voice": voice.speak(line), "timeline": timeline, "code": current}
    if not comp.ok:
        line = replies.FIXED["rejected"] if comp.code else replies.FIXED["busy"]
        return {"outcome": "rejected", "say": line, "voice": voice.speak(line), "reason": comp.reason,
                "timeline": timeline, "code": current}
    g = guard.check(comp.code, sk.args)
    mark("guard", ok=g.ok, reason=g.reason)
    if not g.ok:
        line = replies.FIXED["blocked"]
        return {"outcome": "blocked", "say": line, "voice": voice.speak(line), "reason": g.reason,
                "steps": comp.steps, "proposed": comp.code, "timeline": timeline, "code": current}

    grade, run, probs = _check(sk, comp.code, s["seed"], "teach")
    run_id = _log_run("teach", run)
    mark("sandbox", verdict=run.verdict, elapsed_ms=run.elapsed_ms, run_id=run_id)
    if run.verdict in ("TIMEOUT", "OOM"):
        line = replies.FIXED["dizzy" if run.verdict == "TIMEOUT" else "too_full"]
        return {"outcome": run.verdict.lower(), "say": line, "voice": voice.speak(line), "steps": comp.steps,
                "proposed": comp.code, "grade": grade, "run": {"id": run_id, **run.receipt, "verdict": run.verdict},
                "timeline": timeline, "code": current}

    cls = _read_out(sk, comp.code, s["seed"], run, probs)
    mark("read_out", behaves_like=cls["behaves_like"])
    s["brains"][sk.name] = comp.code
    s["history"][sk.name].append({"right": grade["right"], "at": time.time()})
    trap = cls.get("trap")
    line = replies.score_line(grade["right"], grade["total"]) + " " + replies.echo(
        sk.name, cls["behaves_like"], trap["args"] if trap else None, trap["out"] if trap else None)
    mark("reply")
    return {"outcome": "cured" if grade["right"] == grade["total"] else "partial", "say": line, "voice": voice.speak(line),
            "steps": comp.steps, "code": comp.code, "previous": current, "grade": grade, "read_out": cls,
            "run": {"id": run_id, **run.receipt, "verdict": run.verdict}, "timeline": timeline}


@app.post("/api/quiz")
def quiz(q: SkillReq, request: Request) -> dict:
    _limit(request, 20, "quiz")
    s, sk = _session(q.sid), _skill(q.skill)
    grade, run, _ = _check(sk, s["brains"][sk.name], random.randrange(10 ** 6), "quiz")
    run_id = _log_run("quiz", run)
    grade["rows"] = grade["rows"][:10]
    return {"grade": grade, "run": {"id": run_id, **run.receipt, "verdict": run.verdict}}


@app.post("/api/reset")
def reset(q: SkillReq) -> dict:
    s, sk = _session(q.sid), _skill(q.skill)
    s["brains"][sk.name] = sk.start_code
    s["history"][sk.name] = []
    return {"code": sk.start_code}


@app.post("/api/chip")
def chip(c: Chip, request: Request) -> dict:
    """A judge's bad-advice chip runs through the same guard and sandbox, while a normal maths
    turn runs at the same time to show the host keeps working."""
    _limit(request, 15, "chip")
    s = _session(c.sid)
    fx = fixtures.CHIPS.get(c.chip)
    if not fx:
        raise HTTPException(400, "Unknown test")
    sk = SKILLS[fx["skill"]]
    g = guard.check(fx["code"], sk.args)
    witness = _pool.submit(_check, sk, s["brains"][sk.name], s["seed"], "witness")
    if not g.ok:
        w_grade, w_run, _ = witness.result(timeout=15)
        return {"chip": c.chip, "label": fx["label"], "code": fx["code"], "verdict": "BLOCKED_STATIC",
                "reason": g.reason, "line": g.line, "say": replies.FIXED["blocked"],
                "voice": voice.speak(replies.FIXED["blocked"]),
                "witness": {"verdict": w_run.verdict, "right": w_grade["right"], "total": w_grade["total"]}}
    probs = sk.problems(s["seed"], 40)
    run = sandbox.run(fx["code"], [list(p) for p in probs], f"chip:{c.chip}")
    run_id = _log_run(f"chip:{c.chip}", run)
    w_grade, w_run, _ = witness.result(timeout=15)
    line = replies.FIXED["dizzy" if run.verdict == "TIMEOUT" else "too_full" if run.verdict == "OOM" else "blocked"]
    return {"chip": c.chip, "label": fx["label"], "code": fx["code"], "verdict": run.verdict, "say": line,
            "voice": voice.speak(line), "run": {"id": run_id, **run.receipt, "verdict": run.verdict},
            "witness": {"verdict": w_run.verdict, "right": w_grade["right"], "total": w_grade["total"],
                        "elapsed_ms": w_run.elapsed_ms}}


@app.post("/api/beyond/{name}")
def beyond(name: str, request: Request) -> dict:
    _limit(request, 15, "beyond")
    fx = fixtures.BEYOND.get(name)
    if not fx:
        raise HTTPException(400, "Unknown test")
    run = sandbox.run_raw(fx["script"], f"beyond:{name}")
    run_id = _log_run(f"beyond:{name}", run)
    return {"name": name, "label": fx["label"], "script": fx["script"], "verdict": run.verdict,
            "output": run.receipt.get("output", ""), "run": {"id": run_id, **run.receipt, "verdict": run.verdict}}


@app.get("/api/receipt/{run_id}")
def receipt(run_id: str):
    import json
    if not run_id.isalnum() or len(run_id) > 20:
        raise HTTPException(400, "Bad id")
    row = _db().execute("SELECT receipt FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "No such run")
    return JSONResponse(json.loads(row[0]), headers={"Content-Disposition": f'attachment; filename="ahmes-receipt-{run_id}.json"'})


@app.get("/api/log")
def run_log() -> list:
    rows = _db().execute("SELECT id, at, purpose, verdict, elapsed_ms, container, removed FROM runs ORDER BY at DESC LIMIT 25").fetchall()
    return [{"id": r[0], "at": r[1], "purpose": r[2], "verdict": r[3], "elapsed_ms": r[4], "container": r[5], "removed": bool(r[6])} for r in rows]


@app.get("/api/sandboxes")
def live_sandboxes() -> dict:
    """What `docker ps` shows right now: normally nothing, because every box is destroyed after its task."""
    p = sandbox._docker("ps", "-a", "--filter", "label=ahmes=sandbox", "--format", "{{.Names}} {{.Status}}")
    return {"containers": [l for l in p.stdout.decode().splitlines() if l.strip()]}


@app.get("/audio/{audio_id}.mp3")
def audio(audio_id: str):
    f = voice.file_for(audio_id)
    if not f:
        raise HTTPException(404, "No audio")
    return FileResponse(f, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/health")
def health() -> dict:
    return {"ok": True, "sessions": len(_sessions)}


@app.on_event("startup")
def _startup() -> None:
    sandbox.sweep(0)
    threading.Thread(target=sandbox.sweeper_forever, daemon=True).start()
    for line in replies.FIXED.values():   # pre-render Ahmes's fixed lines
        _pool.submit(voice.speak, line)


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
