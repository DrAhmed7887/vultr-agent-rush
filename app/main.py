"""Teach Ahmes: the orchestrator on the Vultr VM.

One teach turn: child's words -> literal compiler (Vultr Serverless Inference) -> quote check
-> AST guard -> throwaway container -> exact checker -> behaviour read-out -> Ahmes's reply
-> his voice (ElevenLabs). Children's sentences live only in memory and are purged after 24 h.
"""
from __future__ import annotations

import concurrent.futures as cf
import contextlib
import random
import secrets
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import classifier, compiler, fixtures, guard, listen, replies, sandbox, teacher, voice
from .skills import BRIEF, HOMEWORK, IDEAS, KIND, SKILLS, TRICKS, VIEW, YEAR, valid_problem
from .skills_y6 import Y6
from .skills import tricks as trick_table

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path("/var/lib/ahmes/runs.db") if Path("/var/lib/ahmes").exists() else ROOT / "runs.db"
SESSION_TTL_S = 24 * 3600
MAX_SENTENCE = 500
TEACH_SEED = 11   # the fixed 40-problem test from gate G1, so the README's scores reproduce live

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
    with contextlib.closing(_db()) as con, con:
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


GLOBAL_PER_MIN = {"teach": 120, "quiz": 120, "chip": 60, "beyond": 60, "session": 300, "read": 600, "listen": 120}


def _limit(request: Request, per_min: int = 20, bucket: str = "teach") -> None:
    now = time.time()
    g = _rate.setdefault(f"global:{bucket}", deque())
    while g and now - g[0] > 60:
        g.popleft()
    if len(g) >= GLOBAL_PER_MIN.get(bucket, 120):
        raise HTTPException(429, "Ahmes is very busy right now. Try again in a minute.")
    g.append(now)
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
    homework: list[int] | None = Field(default=None, max_length=6)   # the problem he retries
    listen_again: bool = False   # recompile the last sentence with Thoth's note


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
        rows.append({"args": list(p), "problem": sk.show(p), "answer": sk.show_answer(p, c["out"]) if c and status == "ok" else status,
                     "ok": ok, "status": status})
    return {"right": right, "total": len(probs), "rows": rows}


def _check(sk, code: str, seed: int, purpose: str, extra: list | None = None) -> tuple[dict, sandbox.RunResult, list]:
    """Run the 40-problem test in one container. `extra` problems (the homework) ride along in
    the same container after the 40 and are not part of the score."""
    probs = sk.problems(seed, 40)
    run = sandbox.run(code, [list(p) for p in probs] + [list(e) for e in (extra or [])], purpose)
    return _grade(sk, probs, run), run, probs


def _card(sk, args, case: dict | None, prefer: str = "") -> dict:
    """One problem as the child sees it: his answer, right or wrong, and his own reason."""
    out = case.get("out") if case and case.get("status") == "ok" else None
    status = case.get("status") if case else "not_run"
    why = replies.explain(sk.name, args, out, prefer) if out is not None else \
        replies.FIXED["dizzy"] if status == "dizzy" else "Hmm, I didn't get an answer for that one."
    return {"args": list(args), "kind": KIND[sk.name](args), "problem": sk.show(args),
            "his_answer": sk.show_answer(args, out) if out is not None else status,
            "out": out, "ok": out is not None and sk.grade(args, out), "why": why}


def _timed(fn, *a):
    t0 = time.monotonic()
    out = fn(*a)
    return out, int((time.monotonic() - t0) * 1000)


def _picture(sk, args) -> str:
    """What the picture on the child's screen shows, in words, for Thoth's hint."""
    from .skills import dec_text, dec_truth, frac_truth
    if sk.name in Y6:
        return Y6[sk.name]["picture"](args)
    if sk.name == "compare_decimals":
        a, b, tr = dec_text(*args[:3]), dec_text(*args[3:]), dec_truth(args)
        return f"{a} and {b} land on the same spot on the number line" if tr == 0 else \
            f"{a if tr == 1 else b} is further along the number line"
    tv = frac_truth(args)
    return f"fraction bars: really it is {tv.numerator}/{tv.denominator}"


def _thoth(sk, hw, attempts: list, retry: dict | None, outcome: str, aud: dict | None = None) -> dict | None:
    """When Thoth steps in. 1) The code doesn't match the child's words. 2) The child is stuck:
    two or more tries on this homework and it's still wrong (or he keeps getting dizzy)."""
    if aud and aud.get("faithful") is False:
        if aud["missed"]:
            say = f"I'm Thoth, the teacher. Ahmes didn't use all of your words. He missed: “{aud['missed']}”."
            note = f"Your code ignored these words of the child: \"{aud['missed']}\"."
        else:
            say = f"I'm Thoth, the teacher. Ahmes did more than you said: he {aud['added']}."
            note = f"Your code did something the child never said: {aud['added']}."
        return {"kind": "audit", "say": say, "note": note, "action": "listen_again"}
    stuck = len(attempts) >= 2 and (outcome in ("timeout", "oom") or (retry is not None and not retry["ok"]))
    if stuck and hw:
        his = retry or {"his_answer": "he got dizzy" if outcome == "timeout" else "his head got too full", "why": ""}
        h = teacher.hint(sk.show(hw), his["his_answer"], his.get("why", ""), attempts, _picture(sk, hw))
        if h:
            return {"kind": "hint", "say": h}
    return None


def _remember(s: dict, skill: str, sentence: str, outcome: str, right, retry, th) -> None:
    """One line of the lesson report. Kept in memory with the session, never written to disk."""
    s.setdefault("log", {}).setdefault(skill, []).append({
        "at": time.time(), "kind": "teach", "sentence": sentence, "outcome": outcome, "right": right,
        "homework": retry["problem"] if retry else None, "fixed_homework": bool(retry and retry["ok"]),
        "thoth": th["say"] if th else None})


_start: dict[str, dict] = {}


def _start_state(sk) -> dict:
    """His starting brain on the 40-problem test plus the first homework, run once in the sandbox."""
    if sk.name not in _start:
        hw = HOMEWORK[sk.name]
        grade, run, probs = _check(sk, sk.start_code, TEACH_SEED, "start", [hw])
        _log_run("start", run)
        by_i = {c.get("i"): c for c in run.cases}
        card = _card(sk, hw, by_i.get(40), "")
        _start[sk.name] = {"homework": card, "tricks": trick_table(sk.name, probs, [r["ok"] for r in grade["rows"]])}
    return _start[sk.name]


def _read_out(sk, run: sandbox.RunResult, probs: list) -> dict:
    """Which known rule he now behaves like, and his next trap: a problem from this same test
    that he got wrong (preferring one where his rule and the right rule disagree)."""
    outs = {c["i"]: c.get("out") for c in run.cases if c.get("status") == "ok"}
    idx = [i for i in range(len(probs)) if i in outs]
    cls = classifier.classify(sk.name, [probs[i] for i in idx], [outs[i] for i in idx]) if idx else \
        {"behaves_like": "unknown", "label": "no answers to read", "matches": {}, "n": 0, "unknown": 1.0}
    wrong = [i for i in idx if not sk.grade(probs[i], outs[i])]
    pool = [probs[i] for i in wrong]
    probe = classifier.next_probe(sk.name, cls["behaves_like"], pool) or (pool[0] if pool else None)
    trap = None
    if probe is not None:
        out = outs[wrong[pool.index(probe)]]
        trap = {"problem": sk.show(probe), "his_answer": sk.show_answer(probe, out), "args": list(probe), "out": out}
    cls["trap"] = trap
    return cls


@app.post("/api/session")
def new_session(request: Request, resume: str = "") -> dict:
    """A new session, or the same one again if this browser still has a live one (progress is
    kept in the server's memory for 24 hours, never on disk)."""
    _limit(request, 30, "session")
    with _lock:
        old = _sessions.get(resume[:40]) if resume else None
        if old and time.time() - old["created"] <= SESSION_TTL_S:
            sid, sess = resume[:40], old
        else:
            sid = secrets.token_urlsafe(12)
            sess = _sessions[sid] = {"created": time.time(), "seed": TEACH_SEED,
                                     "brains": {k: s.start_code for k, s in SKILLS.items()}, "history": {k: [] for k in SKILLS}}
    progress = sess.setdefault("progress", {})
    out = {}
    for k, sk in SKILLS.items():
        st = _start_state(sk)
        mine = progress.get(k, {})
        card = mine.get("homework") or st["homework"]
        hw = dict(card, voice=voice.speak(card["why"]))
        out[k] = {"title": sk.title, "view": VIEW[k], "year": YEAR[k], "ideas": IDEAS[k],
                  "code": sk.start_code, "current": sess["brains"][k], "welcome": replies.FIXED[f"welcome_{k}"],
                  "voice": voice.speak(replies.FIXED[f"welcome_{k}"]), "homework": hw,
                  "start_homework": st["homework"], "tricks": mine.get("tricks") or st["tricks"],
                  "start_tricks": st["tricks"], "won": bool(mine.get("won"))}
    return {"sid": sid, "resumed": sid == resume, "skills": out}


@app.post("/api/teach")
def teach(t: Teach, request: Request) -> dict:
    _limit(request)
    s, sk = _session(t.sid), _skill(t.skill)
    last = s.setdefault("last", {}).get(sk.name) or {}
    note = ""
    if t.listen_again:
        if not last.get("note"):
            raise HTTPException(400, "Nothing for Ahmes to listen to again.")
        sentence, note = last["sentence"], last["note"]
    else:
        sentence = " ".join(t.sentence.split())
    if not sentence:
        raise HTTPException(400, "Type what Ahmes should do.")
    current = s["brains"][sk.name]
    timeline = []
    t0 = time.monotonic()

    def mark(stage: str, **kw):
        timeline.append({"stage": stage, "ms": int((time.monotonic() - t0) * 1000), **kw})

    hw = tuple(t.homework) if t.homework else None
    if hw is not None and not valid_problem(sk.name, hw):
        raise HTTPException(400, "Bad homework problem")
    safety = _pool.submit(_timed, listen.safe, sentence)
    comp = compiler.compile_sentence(current, sentence, teacher_note=note, brief=BRIEF.get(sk.name, ""))
    mark("compile", model=comp.model, ok=comp.ok, tokens=comp.usage.get("total_tokens"))
    verdict, safety_ms = safety.result(timeout=15)
    mark("safety", verdict=verdict, model=listen.SAFETY_MODEL, took_ms=safety_ms)
    if verdict == "unsafe":   # personal details or unkind words: nothing is compiled or run
        line = replies.FIXED["unkind"]
        return {"outcome": "unkind", "say": line, "voice": voice.speak(line), "timeline": timeline, "code": current}
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

    watch = _pool.submit(teacher.audit, sentence, current, comp.code, comp.steps)   # Thoth checks while the sandbox runs
    grade, run, probs = _check(sk, comp.code, s["seed"], "teach", [hw] if hw else None)
    run_id = _log_run("teach", run)
    mark("sandbox", verdict=run.verdict, elapsed_ms=run.elapsed_ms, run_id=run_id)
    aud = watch.result(timeout=25)
    mark("teacher", model=aud["model"], took_ms=aud["ms"], faithful=aud["faithful"])
    attempts = s.setdefault("attempts", {}).setdefault(f"{sk.name}:{hw}", [])
    if not t.listen_again:
        attempts.append(sentence)
    statuses = {c.get("status") for c in run.cases if c.get("i", 0) < 40}
    if run.verdict == "TIMEOUT" or "dizzy" in statuses:
        outcome = "timeout"
    elif run.verdict == "OOM" or "too_full" in statuses:
        outcome = "oom"
    else:
        outcome = ""
    if outcome:   # stopped by the container limit or the per-case timer inside it: don't keep this brain
        line = replies.FIXED["dizzy" if outcome == "timeout" else "too_full"]
        s["last"][sk.name] = {"sentence": sentence}
        th = _thoth(sk, hw, attempts, None, outcome)
        _remember(s, sk.name, sentence, outcome, None, None, th)
        return {"outcome": outcome, "say": line, "teacher": th, "audit": aud, "voice": voice.speak(line), "steps": comp.steps,
                "proposed": comp.code, "grade": grade, "run": {"id": run_id, **run.receipt, "verdict": run.verdict},
                "timeline": timeline, "code": current}
    if run.verdict != "OK" or any(c.get("i") == -1 for c in run.cases):
        line = replies.FIXED["busy" if run.verdict == "BUSY" else "rejected"]
        return {"outcome": "rejected", "say": line, "voice": voice.speak(line), "reason": run.verdict,
                "steps": comp.steps, "proposed": comp.code, "timeline": timeline, "code": current}

    cls = _read_out(sk, run, probs)
    mark("read_out", behaves_like=cls["behaves_like"])
    s["brains"][sk.name] = comp.code
    s["history"][sk.name].append({"right": grade["right"], "at": time.time()})
    trap = cls.get("trap")
    line = replies.score_line(grade["right"], grade["total"]) + " " + replies.echo(
        sk.name, cls["behaves_like"], trap["args"] if trap else None, trap["out"] if trap else None)
    by_i = {c.get("i"): c for c in run.cases}
    retry = _card(sk, hw, by_i.get(40), cls["behaves_like"]) if hw else None
    if retry:
        retry["voice"] = voice.speak(retry["why"])
    th = _thoth(sk, hw, attempts, retry, "", aud)
    s["last"][sk.name] = {"sentence": sentence, "note": th.get("note", "") if th else ""}
    if th and th.get("kind") == "audit":
        mark("teacher_steps_in", why="code doesn't match the words")
    mark("reply")
    tr = trick_table(sk.name, probs, [r["ok"] for r in grade["rows"]])
    prog = s.setdefault("progress", {}).setdefault(sk.name, {})
    prog["tricks"] = tr
    if retry:
        prog["homework"] = {k: v for k, v in retry.items() if k != "voice"}
    _remember(s, sk.name, sentence, "cured" if grade["right"] == grade["total"] else "partial", grade["right"], retry, th)
    return {"outcome": "cured" if grade["right"] == grade["total"] else "partial", "say": line, "voice": voice.speak(line),
            "steps": comp.steps, "code": comp.code, "previous": current, "grade": grade, "read_out": cls,
            "retry": retry, "teacher": th, "audit": aud, "tricks": tr,
            "run": {"id": run_id, **run.receipt, "verdict": run.verdict}, "timeline": timeline}


@app.post("/api/quiz")
def quiz(q: SkillReq, request: Request) -> dict:
    _limit(request, 20, "quiz")
    s, sk = _session(q.sid), _skill(q.skill)
    grade, run, probs = _check(sk, s["brains"][sk.name], random.randrange(10 ** 6), "quiz")
    run_id = _log_run("quiz", run)
    by_i = {c.get("i"): c for c in run.cases}
    prefer = _read_out(sk, run, probs)["behaves_like"]   # so each card's reason matches his overall rule
    cards = []
    for key, name, _ in TRICKS[sk.name]:   # one card per trick: the first he got wrong, else the first of that kind
        idx = [i for i, p in enumerate(probs) if KIND[sk.name](p) == key]
        if not idx:
            continue
        pick = next((i for i in idx if not grade["rows"][i]["ok"]), idx[0])
        card = _card(sk, probs[pick], by_i.get(pick), prefer)
        cards.append({**card, "trick": key, "trick_name": name})
    nxt = next((c for c in cards if not c["ok"]), None)
    tr = trick_table(sk.name, probs, [r["ok"] for r in grade["rows"]])
    prog = s.setdefault("progress", {}).setdefault(sk.name, {})
    prog["tricks"] = tr
    prog["won"] = prog.get("won", False) or nxt is None
    if nxt:
        prog["homework"] = dict(nxt)
        nxt["voice"] = voice.speak(nxt["why"])
    s.setdefault("log", {}).setdefault(sk.name, []).append(
        {"at": time.time(), "kind": "quiz", "right": grade["right"], "total": grade["total"]})
    return {"grade": grade, "cards": cards, "next_homework": nxt,
            "tricks": tr, "run": {"id": run_id, **run.receipt, "verdict": run.verdict}}


@app.post("/api/listen")
async def listen_to_child(request: Request, sid: str = "") -> dict:
    """The child's recording -> text, by Vultr's omni model. The audio isn't stored."""
    _limit(request, 20, "listen")
    _session(sid[:40])
    wav = await request.body()
    try:
        text = await run_in_threadpool(listen.hear, wav)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except Exception:  # noqa: BLE001
        raise HTTPException(503, "Ahmes can't hear right now. Type it instead.") from None
    return {"text": text}


@app.post("/api/reset")
def reset(q: SkillReq) -> dict:
    s, sk = _session(q.sid), _skill(q.skill)
    s["brains"][sk.name] = sk.start_code
    s["history"][sk.name] = []
    s.get("progress", {}).pop(sk.name, None)
    s.get("log", {}).pop(sk.name, None)
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
        _log_run("witness", w_run)
        return {"chip": c.chip, "label": fx["label"], "code": fx["code"], "verdict": "BLOCKED_STATIC",
                "reason": g.reason, "line": g.line, "say": replies.FIXED["blocked"],
                "voice": voice.speak(replies.FIXED["blocked"]),
                "witness": {"verdict": w_run.verdict, "right": w_grade["right"], "total": w_grade["total"]}}
    probs = sk.problems(s["seed"], 40)
    run = sandbox.run(fx["code"], [list(p) for p in probs], f"chip:{c.chip}")
    run_id = _log_run(f"chip:{c.chip}", run)
    w_grade, w_run, _ = witness.result(timeout=15)
    _log_run("witness", w_run)
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


@app.get("/api/report")
def report(request: Request, sid: str = "") -> dict:
    """For a parent or teacher: what the child taught, what Ahmes learned, when Thoth stepped in."""
    _limit(request, 30, "read")
    s = _session(sid[:40])
    lessons = []
    for k, sk in SKILLS.items():
        log = s.get("log", {}).get(k, [])
        if not log:
            continue
        prog = s.get("progress", {}).get(k, {})
        tr = prog.get("tricks") or _start_state(sk)["tricks"]
        lessons.append({"skill": k, "title": sk.title, "year": YEAR[k], "won": bool(prog.get("won")),
                        "tricks": [{"name": t["name"], "learned": t["learned"]} for t in tr], "turns": log})
    return {"lessons": lessons, "made_at": time.time()}


@app.get("/api/receipt/{run_id}")
def receipt(run_id: str, request: Request):
    import json
    _limit(request, 60, "read")
    if not run_id.isalnum() or len(run_id) > 20:
        raise HTTPException(400, "Bad id")
    with contextlib.closing(_db()) as con:
        row = con.execute("SELECT receipt FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "No such run")
    return JSONResponse(json.loads(row[0]), headers={"Content-Disposition": f'attachment; filename="ahmes-receipt-{run_id}.json"'})


@app.get("/api/log")
def run_log(request: Request) -> list:
    _limit(request, 60, "read")
    with contextlib.closing(_db()) as con:
        rows = con.execute("SELECT id, at, purpose, verdict, elapsed_ms, container, removed FROM runs ORDER BY at DESC LIMIT 25").fetchall()
    return [{"id": r[0], "at": r[1], "purpose": r[2], "verdict": r[3], "elapsed_ms": r[4], "container": r[5], "removed": bool(r[6])} for r in rows]


@app.get("/api/sandboxes")
def live_sandboxes(request: Request) -> dict:
    """What `docker ps` shows right now: normally nothing, because every box is destroyed after its task."""
    _limit(request, 60, "read")
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

    def warm() -> None:   # each lesson's starting brain, once, so the first visitor doesn't wait
        for sk in SKILLS.values():
            try:
                voice.speak(_start_state(sk)["homework"]["why"])
            except Exception:  # noqa: BLE001
                pass
    _pool.submit(warm)


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
