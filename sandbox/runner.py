"""Runs inside the throwaway container. Reads {"code", "inputs"} as JSON on stdin and prints one
JSON line per test case, flushed, so partial results survive a kill.

Layers inside the box: a stripped __builtins__ (no import, open, eval...), and a 0.25 s soft
timer per case. The container itself has no network, no secrets, a read-only disk and caps on
memory, CPU, processes and wall time; those are the real boundary.
"""
import json
import signal
import sys


def digit(digits, places, k):
    if k < 1 or k > places:
        return 0
    return digits // (10 ** (places - k)) % 10


def pad(digits, places, to):
    if to <= places:
        return digits
    return digits * (10 ** (to - places))


def apply(op, x, y):
    """One operation: 1 is +, 2 is -, 3 is x, 4 is divide (whole numbers)."""
    if op == 1:
        return x + y
    if op == 2:
        return x - y
    if op == 3:
        return x * y
    if op == 4:
        return x // y
    return 0


def gcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


SAFE_BUILTINS = {"abs": abs, "min": min, "max": max, "range": range, "True": True, "False": False, "None": None}
LIMIT = 10 ** 12


class CaseTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise CaseTimeout()


def _clean(out):
    if isinstance(out, bool):
        return out
    if isinstance(out, int):
        return out if abs(out) <= LIMIT else "too_big"
    if isinstance(out, tuple) and len(out) <= 4:
        return [_clean(x) for x in out]
    return "bad_type"


def main():
    req = json.loads(sys.stdin.read())
    env = {"__builtins__": SAFE_BUILTINS, "digit": digit, "pad": pad, "gcd": gcd, "apply": apply}
    try:
        exec(compile(req["code"], "<ahmes>", "exec"), env)
        fn = env["solve"]
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"i": -1, "status": "error", "out": type(e).__name__}), flush=True)
        return
    signal.signal(signal.SIGALRM, _alarm)
    for i, args in enumerate(req["inputs"]):
        status, out = "ok", None
        signal.setitimer(signal.ITIMER_REAL, 0.25)
        try:
            out = _clean(fn(*args))
        except CaseTimeout:
            status = "dizzy"
        except MemoryError:
            status = "too_full"
        except Exception as e:  # noqa: BLE001
            status, out = "error", type(e).__name__
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        print(json.dumps({"i": i, "status": status, "out": out}), flush=True)


if __name__ == "__main__":
    main()
