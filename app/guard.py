"""Static guard: Ahmes's brain may only be one small maths function.

This is a first layer, not the security boundary. In-process guards are known to be bypassable,
which is why every patch still runs in a throwaway, network-less container.
`While` is allowed on purpose: no static check can tell whether a loop ends, so time is the sandbox's job.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

MAX_LINES = 40
MAX_BYTES = 2048
MAX_CONST = 10 ** 6
ALLOWED_CALLS = {"abs", "min", "max", "range", "digit", "pad", "gcd"}

ALLOWED_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AugAssign,
    ast.If, ast.While, ast.For, ast.Break, ast.Continue, ast.Pass, ast.Expr,
    ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Call, ast.Name, ast.Load,
    ast.Store, ast.Tuple, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not,
    ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str = ""
    line: int = 0


def _fail(reason: str, node: ast.AST | None = None) -> GuardResult:
    return GuardResult(False, reason, getattr(node, "lineno", 0))


def check(code: str, args: tuple[str, ...]) -> GuardResult:
    if len(code.encode()) > MAX_BYTES or code.count("\n") + 1 > MAX_LINES:
        return _fail("too long")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return GuardResult(False, f"not valid code: {e.msg}", e.lineno or 0)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return _fail("must be exactly one function")
    fn = tree.body[0]
    if fn.name != "solve":
        return _fail("the function must be called solve", fn)
    a = fn.args
    if (a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg or a.defaults or a.kw_defaults
            or fn.decorator_list or fn.returns or tuple(x.arg for x in a.args) != args):
        return _fail("wrong inputs for this skill", fn)
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            return _fail(f"'{type(node).__name__}' isn't allowed in Ahmes's brain", node)
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return _fail("names can't start with __", node)
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                continue
            if not isinstance(v, int) or abs(v) > MAX_CONST:
                return _fail("only small whole numbers are allowed", node)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS or node.keywords:
                return _fail("that word isn't in Ahmes's brain dictionary", node)
        if isinstance(node, ast.For):
            it = node.iter
            if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"):
                return _fail("loops can only count with range()", node)
            if not isinstance(node.target, ast.Name):
                return _fail("loop variable must be a simple name", node)
    return GuardResult(True)
