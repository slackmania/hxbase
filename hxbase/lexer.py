"""HxBase lexer: kifejezes-tokenizer xBase dialektushoz."""

import re

KEYWORDS = {
    "AND", "OR", "NOT",
}

TOKEN_SPEC = [
    ("SKIP_WS",      r"[ \t]+"),
    ("STRING_DQ",    r'"(?:[^"\\]|\\.)*"'),
    ("STRING_SQ",    r"'(?:[^'\\]|\\.)*'"),
    ("DATE_LIT",     r"\{\^[0-9]{4}-[0-9]{2}-[0-9]{2}\}"),
    ("NUMBER",       r"\d+\.\d+|\d+|\.\d+"),
    ("LOGICAL",      r"\.(?:T|F|Y|N|TRUE|FALSE)\."),
    ("NE",           r"<>|!=|#"),
    ("LE",           r"<="),
    ("GE",           r">="),
    ("ASSIGN_EQ",    r"=="),
    ("ARROW",        r"->"),
    ("AND",          r"\.AND\."),
    ("OR",           r"\.OR\."),
    ("NOT",          r"\.NOT\.|!"),
    ("CONTAINS",     r"\$"),
    ("LE2",          r"<"),
    ("GE2",          r">"),
    ("EQ",           r"="),
    ("PLUS",         r"\+"),
    ("MINUS",        r"-"),
    ("STAR",         r"\*"),
    ("SLASH",        r"/"),
    ("PERCENT",      r"%"),
    ("POWER",        r"\^"),
    ("LPAREN",       r"\("),
    ("RPAREN",       r"\)"),
    ("LBRACK",       r"\["),
    ("RBRACK",       r"\]"),
    ("COMMA",        r","),
    ("COLON",        r":"),
    ("DOT",          r"\."),
    ("IDENT",        r"[A-Za-z_][A-Za-z0-9_]*"),
]

MASTER = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC), re.IGNORECASE)


class Tok:
    __slots__ = ("kind", "value", "pos")
    def __init__(self, kind, value, pos=0):
        self.kind = kind
        self.value = value
        self.pos = pos
    def __repr__(self):
        return f"Tok({self.kind},{self.value!r})"


def tokenize(s):
    toks = []
    for m in MASTER.finditer(s):
        kind = m.lastgroup
        val = m.group()
        if kind == "SKIP_WS":
            continue
        toks.append(Tok(kind, val, m.start()))
    return toks
