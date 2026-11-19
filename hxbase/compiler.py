"""HxBase compiler: .prg -> p-kod (JSON)."""

import json
from .parser import parse_program

PCODE_VERSION = 1


def compile_source(source):
    stmts = parse_program(source)
    return {"version": PCODE_VERSION, "code": stmts}


def compile_file(path, encoding="utf-8"):
    with open(path, encoding=encoding) as f:
        return compile_source(f.read())


def save_pcode(pcode, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pcode, f, ensure_ascii=False, indent=1)


def load_pcode(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
