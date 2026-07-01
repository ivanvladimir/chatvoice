"""
parser.py — command-language parser with pipe chaining support.

Grammar (informal):
    script     ::= line*
    line       ::= command ("|" command)*
    command    ::= ("if" | "while") condition "then" simple_cmd | simple_cmd
    simple_cmd ::= WORD arg*
    condition  ::= clause ("or" clause)*
    clause     ::= ["not"] WORD [OP WORD]
    OP         ::= "==" | "!=" | "<=" | ">=" | "<" | ">"
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Optional, Literal, List


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Clause:
    """A single boolean clause: [not] left [op right]."""
    left: str
    negate: bool = False
    op: Optional[str] = None
    right: Optional[str] = None

    def __str__(self) -> str:
        parts = ["not"] if self.negate else []
        parts.append(self.left)
        if self.op and self.right is not None:
            parts += [self.op, self.right]
        return " ".join(parts)


@dataclass(frozen=True)
class Condition:
    """One or more clauses joined by OR."""
    clauses: tuple[Clause, ...]

    def __str__(self) -> str:
        return " or ".join(str(c) for c in self.clauses)


# The kind of guard a command carries, if any.
ConditionType = Literal["if", "while"]


@dataclass(frozen=True)
class Command:
    """A single command with optional args and an optional guard condition.

    ``condition_type`` tells you *which* keyword introduced the guard:
    ``"if"``, ``"while"`` or ``None`` (unguarded command).
    """
    name: str
    _command: str
    args: tuple[str, ...] = field(default_factory=tuple)
    condition: Optional[Condition] = None
    condition_type: Optional[ConditionType] = None


@dataclass(frozen=True)
class Chain:
    """A sequence of commands on one line, separated by '|'."""
    commands: List[Command, ...]

    def __str__(self) -> str:
        return " | ".join(str(c) for c in self.commands)


Line = Chain


# ---------------------------------------------------------------------------
# Tokeniser helpers
# ---------------------------------------------------------------------------

_OP_RE = re.compile(r"==|!=|<=|>=|<|>")
# Captures the leading keyword (if / while) so we can record its type.
_IF_WHILE_THEN_RE = re.compile(
    r"^(if|while)\s+(.+?)\s+then\s+(.+)$",
    re.IGNORECASE,
)


def _tokenize(text: str) -> list[str]:
    """Split *text* into tokens, keeping quoted strings together."""
    lex = shlex.shlex(text, posix=True)
    lex.whitespace_split = True
    lex.whitespace = " \t"
    return list(lex)


def _split_pipe(line: str) -> list[str]:
    """Split *line* on ``|`` while respecting quoted strings."""
    segments: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_char = ""

    for ch in line:
        if ch in ('"', "'") and not in_quote:
            in_quote, quote_char = True, ch
        elif ch == quote_char and in_quote:
            in_quote = False
        if ch == "|" and not in_quote:
            segments.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        segments.append("".join(current).strip())

    return [s for s in segments if s]


# ---------------------------------------------------------------------------
# Condition / clause parsers
# ---------------------------------------------------------------------------

def _parse_clause(text: str) -> Clause:
    """Parse a single clause such as ``not status == "good"``."""
    text = text.strip()
    negate = text.lower().startswith("not ")
    if negate:
        text = text[4:].lstrip()

    match = _OP_RE.search(text)
    if match:
        op = match.group()
        left = text[: match.start()].strip()
        right = text[match.end():].strip()
        return Clause(left=left, negate=negate, op=op, right=right)

    return Clause(left=text.strip(), negate=negate)


def _parse_condition(text: str) -> Condition:
    """Parse a condition, which may contain several OR-joined clauses."""
    raw_clauses = re.split(r"\bor\b", text, flags=re.IGNORECASE)
    clauses = tuple(_parse_clause(c) for c in raw_clauses)
    return Condition(clauses=clauses)


# ---------------------------------------------------------------------------
# Command parser
# ---------------------------------------------------------------------------

def _parse_command(text: str) -> Command:
    """Parse one command segment (no ``|`` characters)."""
    text = text.strip()
    m = _IF_WHILE_THEN_RE.match(text)
    if m:
        # group(1) is "if" or "while" (case-insensitive) -> normalise to lower.
        cond_type: ConditionType = m.group(1).lower()  # type: ignore[assignment]
        condition = _parse_condition(m.group(2))
        tokens = _tokenize(m.group(3))
        if not tokens:
            raise ValueError(f"Empty command body in: {text!r}")
        return Command(
            name=tokens[0],
            _command=text,
            args=tuple(tokens[1:]),
            condition=condition,
            condition_type=cond_type,
        )

    tokens = _tokenize(text)
    if not tokens:
        raise ValueError(f"Empty command in: {text!r}")
    return Command(
        name=tokens[0],
        _command=text,
        args=tuple(tokens[1:]),
        condition=None,
        condition_type=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_line(line: str) -> Line:
    """Parse one source line into a :class:`Chain` of commands."""
    segments = _split_pipe(line)
    commands = list(_parse_command(seg) for seg in segments)
    return Chain(commands=commands)


def parse_script(source: str) -> list[Line]:
    """Parse a multi-line script, skipping blank lines and comments (``#``)."""
    lines: list[Line] = []
    for raw in source.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(parse_line(stripped))
    return lines
