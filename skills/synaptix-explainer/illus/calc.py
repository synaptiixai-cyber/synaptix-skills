"""Safe deterministic arithmetic evaluator for synaptix-explainer specs.

Grammar:
    expr    := term (('+' | '-') term)*
    term    := power (('*' | '/') power)*
    power   := unary ('^' unary)?          # right operand must be integer, |e| <= 6
    unary   := ('-' | '+') unary | postfix
    postfix := atom '%'?                   # 12% -> 0.12
    atom    := NUMBER | '(' expr ')' | FUNC '(' expr (',' expr)* ')'
    FUNC    := round | min | max | abs | sum
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

MAX_EXPR_CHARS = 60
MAX_TOKENS = 40
MAX_DEPTH = 6
MAX_ABS_VALUE = Decimal("1000000000000000")
MAX_EXPONENT = 6
QUANTIZE_STEP = Decimal("0.000001")

ALLOWED_FUNCS = ("round", "min", "max", "abs", "sum")
DIGITS = "0123456789"
IDENT_START = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
IDENT_CHARS = IDENT_START + DIGITS


class CalcError(Exception):
    """Structured calculator error carrying code, message, and fix hint."""

    def __init__(self, code: str, message: str, fix: str) -> None:
        self.args = (message,)
        self.code = code
        self.message = message
        self.fix = fix


def quantize_dec(val: Decimal) -> Decimal:
    if not val.is_finite():
        raise CalcError(
            "E_CALC_RANGE",
            "Result is not a finite number",
            "Use finite numbers within +/-1e15",
        )
    if abs(val) > MAX_ABS_VALUE:
        raise CalcError(
            "E_CALC_RANGE",
            "Result magnitude exceeds 1e15 limit",
            "Keep numeric values within +/-1e15",
        )
    q = val.quantize(QUANTIZE_STEP, rounding=ROUND_HALF_UP)
    if q == Decimal("0"):
        return Decimal("0")
    return q


def dec_to_number(val: Decimal) -> Any:
    q = quantize_dec(val)
    if q == q.to_integral_value():
        return int(q)
    return float(q)


def tokenize(expr: str) -> List[Tuple[str, str, int]]:
    if len(expr) > MAX_EXPR_CHARS:
        raise CalcError(
            "E_CALC_RANGE",
            f"Expression exceeds {MAX_EXPR_CHARS} characters",
            "Shorten the arithmetic expression or pass the computed number",
        )
    tokens: List[Tuple[str, str, int]] = []
    n = len(expr)
    i = 0
    while i < n:
        ch = expr[i]
        if ch in " \t\r\n":
            i = i + 1
            continue
        if len(tokens) >= MAX_TOKENS:
            raise CalcError(
                "E_CALC_RANGE",
                f"Expression exceeds {MAX_TOKENS} tokens",
                "Simplify the arithmetic expression",
            )
        if ch in DIGITS or ch == ".":
            start = i
            dot_seen = False
            while i < n and (expr[i] in DIGITS or expr[i] == "."):
                if expr[i] == ".":
                    if dot_seen:
                        raise CalcError(
                            "E_CALC_SYNTAX",
                            f"Invalid number literal at position {start}",
                            "Use plain decimal numbers like 12.5 or 100",
                        )
                    dot_seen = True
                i = i + 1
            if i < n and expr[i] in ("e", "E"):
                if dot_seen and i - start == 1:
                    raise CalcError(
                        "E_CALC_SYNTAX",
                        f"Standalone '.' at position {start}",
                        "Write a full decimal number such as 0.5",
                    )
                i = i + 1
                if i < n and expr[i] in ("+", "-"):
                    i = i + 1
                exp_start = i
                while i < n and expr[i] in DIGITS:
                    i = i + 1
                if i == exp_start:
                    raise CalcError(
                        "E_CALC_SYNTAX",
                        f"Incomplete exponent at position {start}",
                        "Use valid scientific notation like 1.5e3 or a plain number",
                    )
            lit = expr[start:i]
            if lit == ".":
                raise CalcError(
                    "E_CALC_DENIED",
                    f"Attribute/dot operator '.' is not allowed at position {start}",
                    "Use numbers and arithmetic operators (+, -, *, /, ^, %) only",
                )
            tokens.append(("NUM", lit, start))
            continue

        if ch in IDENT_START:
            start = i
            while i < n and expr[i] in IDENT_CHARS:
                i = i + 1
            ident = expr[start:i]
            if ident in ALLOWED_FUNCS:
                tokens.append(("FUNC", ident, start))
            else:
                raise CalcError(
                    "E_CALC_DENIED",
                    f"'{ident}' is not allowed at position {start}",
                    "Use a number, arithmetic (+ - * / ^ %), or round/min/max/abs/sum",
                )
            continue

        if ch == "*" and i + 1 < n and expr[i + 1] == "*":
            raise CalcError(
                "E_CALC_DENIED",
                f"'**' is not allowed at position {i}",
                "Use '^' with an integer exponent between -6 and 6 (e.g. 2^3)",
            )

        if ch in "+-*/^%(),":
            tokens.append(("OP", ch, i))
            i = i + 1
            continue

        raise CalcError(
            "E_CALC_DENIED",
            f"Character '{ch}' is not allowed at position {i}",
            "Use only digits, +, -, *, /, ^, %, parentheses, and round/min/max/abs/sum",
        )

    if not tokens:
        raise CalcError(
            "E_CALC_SYNTAX",
            "Empty numeric expression",
            "Provide a number such as 42 or arithmetic like 12*4",
        )
    return tokens


class Parser:
    """Recursive-descent parser for safe Decimal expressions."""

    def __init__(self, tokens: List[Tuple[str, str, int]]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.depth = 0

    def peek(self) -> Optional[Tuple[str, str, int]]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self) -> Tuple[str, str, int]:
        tok = self.tokens[self.pos]
        self.pos = self.pos + 1
        return tok

    def enter(self, pos: int) -> None:
        self.depth = self.depth + 1
        if self.depth > MAX_DEPTH:
            raise CalcError(
                "E_CALC_RANGE",
                f"Expression nesting exceeds maximum depth {MAX_DEPTH} at position {pos}",
                "Flatten nested parentheses or function calls",
            )

    def leave(self) -> None:
        self.depth = self.depth - 1

    def parse(self) -> Decimal:
        val = self.parse_expr()
        rem = self.peek()
        if rem is not None:
            raise CalcError(
                "E_CALC_SYNTAX",
                f"Unexpected token '{rem[1]}' at position {rem[2]}",
                "Use valid arithmetic like 120+15 or round(19.4*3, 1)",
            )
        return quantize_dec(val)

    def parse_expr(self) -> Decimal:
        left = self.parse_term()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] == "OP" and tok[1] in ("+", "-"):
                self.consume()
                right = self.parse_term()
                left = quantize_dec(left + right if tok[1] == "+" else left - right)
            else:
                break
        return left

    def parse_term(self) -> Decimal:
        left = self.parse_power()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] == "OP" and tok[1] in ("*", "/"):
                op_tok = self.consume()
                right = self.parse_power()
                if op_tok[1] == "*":
                    left = quantize_dec(left * right)
                else:
                    if right == Decimal("0"):
                        raise CalcError(
                            "E_CALC_RANGE",
                            f"Division by zero at position {op_tok[2]}",
                            "Ensure divisors are non-zero",
                        )
                    left = quantize_dec(left / right)
            else:
                break
        return left

    def parse_power(self) -> Decimal:
        base = self.parse_unary()
        tok = self.peek()
        if tok is not None and tok[0] == "OP" and tok[1] == "^":
            op_tok = self.consume()
            exp = self.parse_unary()
            if exp != exp.to_integral_value() or abs(exp) > Decimal(MAX_EXPONENT):
                raise CalcError(
                    "E_CALC_RANGE",
                    f"Exponent at position {op_tok[2]} must be an integer with |e| <= {MAX_EXPONENT}",
                    "Use an integer exponent between -6 and 6",
                )
            exp_int = int(exp)
            if base == Decimal("0") and exp_int < 0:
                raise CalcError(
                    "E_CALC_RANGE",
                    f"Zero cannot be raised to a negative power at position {op_tok[2]}",
                    "Use a non-zero base or non-negative exponent",
                )
            base = quantize_dec(base ** exp_int)
        return base

    def parse_unary(self) -> Decimal:
        tok = self.peek()
        if tok is not None and tok[0] == "OP" and tok[1] in ("+", "-"):
            op_tok = self.consume()
            self.enter(op_tok[2])
            inner = self.parse_unary()
            self.leave()
            return -inner if op_tok[1] == "-" else inner
        return self.parse_postfix()

    def parse_postfix(self) -> Decimal:
        val = self.parse_atom()
        tok = self.peek()
        if tok is not None and tok[0] == "OP" and tok[1] == "%":
            self.consume()
            val = quantize_dec(val / Decimal("100"))
        return val

    def parse_atom(self) -> Decimal:
        tok = self.peek()
        if tok is None:
            raise CalcError(
                "E_CALC_SYNTAX",
                "Unexpected end of expression",
                "Complete the arithmetic expression or pass a plain number",
            )
        kind, text_val, pos = tok
        if kind == "NUM":
            self.consume()
            try:
                dec = Decimal(text_val)
            except Exception:
                raise CalcError(
                    "E_CALC_SYNTAX",
                    f"Invalid number '{text_val}' at position {pos}",
                    "Use a plain decimal number such as 42 or 3.14",
                ) from None
            return quantize_dec(dec)

        if kind == "OP" and text_val == "(":
            self.consume()
            self.enter(pos)
            val = self.parse_expr()
            self.leave()
            close_tok = self.peek()
            if close_tok is None or close_tok[0] != "OP" or close_tok[1] != ")":
                raise CalcError(
                    "E_CALC_SYNTAX",
                    f"Unclosed '(' starting at position {pos}",
                    "Add the matching closing ')'",
                )
            self.consume()
            return val

        if kind == "FUNC":
            self.consume()
            open_tok = self.peek()
            if open_tok is None or open_tok[0] != "OP" or open_tok[1] != "(":
                raise CalcError(
                    "E_CALC_SYNTAX",
                    f"Function '{text_val}' must be followed by '(' at position {pos}",
                    f"Call {text_val}(...) with parentheses",
                )
            self.consume()
            self.enter(pos)
            args: List[Decimal] = []
            if self.peek() is not None and self.peek()[1] == ")":
                raise CalcError(
                    "E_CALC_SYNTAX",
                    f"Function '{text_val}' requires at least one argument at position {pos}",
                    f"Pass valid numeric arguments to {text_val}(...)",
                )
            while True:
                args.append(self.parse_expr())
                sep = self.peek()
                if sep is not None and sep[0] == "OP" and sep[1] == ",":
                    self.consume()
                    continue
                break
            close_tok = self.peek()
            if close_tok is None or close_tok[0] != "OP" or close_tok[1] != ")":
                raise CalcError(
                    "E_CALC_SYNTAX",
                    f"Missing ')' for {text_val}(...) starting at position {pos}",
                    "Close function arguments with ')'",
                )
            self.consume()
            self.leave()
            return apply_func(text_val, args, pos)

        raise CalcError(
            "E_CALC_SYNTAX",
            f"Unexpected token '{text_val}' at position {pos}",
            "Use a plain number or valid arithmetic like 12.5*4",
        )


def apply_func(name: str, args: List[Decimal], pos: int) -> Decimal:
    if name == "abs":
        if len(args) != 1:
            raise CalcError(
                "E_CALC_SYNTAX",
                f"abs() takes exactly 1 argument at position {pos}",
                "Use abs(x) with one argument",
            )
        return quantize_dec(abs(args[0]))

    if name == "round":
        if len(args) == 1:
            return quantize_dec(args[0].quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if len(args) == 2:
            places_dec = args[1]
            if places_dec != places_dec.to_integral_value() or places_dec < 0 or places_dec > 6:
                raise CalcError(
                    "E_CALC_RANGE",
                    f"round() precision must be an integer 0..6 at position {pos}",
                    "Use round(x) or round(x, 2) with 0 to 6 decimals",
                )
            places = int(places_dec)
            step = Decimal("1") if places == 0 else Decimal("0." + ("0" * (places - 1)) + "1")
            return quantize_dec(args[0].quantize(step, rounding=ROUND_HALF_UP))
        raise CalcError(
            "E_CALC_SYNTAX",
            f"round() takes 1 or 2 arguments at position {pos}",
            "Use round(x) or round(x, digits)",
        )

    if name == "min":
        return quantize_dec(min(args))
    if name == "max":
        return quantize_dec(max(args))
    if name == "sum":
        total = Decimal("0")
        for item in args:
            total = quantize_dec(total + item)
        return total

    raise CalcError(
        "E_CALC_DENIED",
        f"Function '{name}' is not allowed at position {pos}",
        "Allowed functions: round, min, max, abs, sum",
    )


def eval_value(raw: Any) -> Any:
    """Evaluate a JSON number or short arithmetic string into int | float."""
    if isinstance(raw, bool) or raw is None:
        raise CalcError(
            "E_TYPE",
            "Expected a number or arithmetic string, got boolean/null",
            "Provide a numeric value like 42 or '12.5*4'",
        )
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and (raw != raw or raw == float("inf") or raw == float("-inf")):
            raise CalcError(
                "E_CALC_RANGE",
                "NaN and Infinity are not allowed",
                "Provide a finite number within +/-1e15",
            )
        try:
            dec = Decimal(str(raw))
        except Exception:
            raise CalcError(
                "E_CALC_SYNTAX",
                "Invalid numeric value",
                "Provide a finite decimal number",
            ) from None
        return dec_to_number(dec)

    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise CalcError(
                "E_CALC_SYNTAX",
                "Numeric string cannot be empty",
                "Provide a number like 42 or arithmetic like 12*4",
            )
        tokens = tokenize(stripped)
        dec = Parser(tokens).parse()
        return dec_to_number(dec)

    raise CalcError(
        "E_TYPE",
        "Expected number or arithmetic string",
        "Provide a plain number (e.g. 98) or arithmetic string (e.g. '120+15')",
    )
