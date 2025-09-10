# src/tools/calculator.py
import ast
import operator as op

ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}

def safe_eval(expr: str):
    """
    Evaluate math expressions safely (no __import__ or names).
    """
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            oper = ALLOWED_OPERATORS[type(node.op)]
            return oper(left, right)
        if isinstance(node, ast.UnaryOp):
            oper = ALLOWED_OPERATORS[type(node.op)]
            return oper(_eval(node.operand))
        raise ValueError("Unsupported expression")

    parsed = ast.parse(expr, mode="eval")
    return _eval(parsed.body)
