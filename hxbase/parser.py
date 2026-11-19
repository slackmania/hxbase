"""HxBase parser: sor-orientalt xBase parser AST-vel."""

import re
from .lexer import tokenize

CMP_OPS = {"=", "==", "<>", "!=", "#", "<", ">", "<=", ">="}


def strip_line(s):
    # && komment levagasa (stringen kivul)
    out, q = [], None
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            out.append(c)
            if c == q:
                q = None
            i += 1
            continue
        if c in "\"'":
            q = c
            out.append(c)
            i += 1
            continue
        if c == "&" and i + 1 < len(s) and s[i + 1] == "&":
            break
        if c == "/" and i + 1 < len(s) and s[i + 1] == "/":
            break
        out.append(c)
        i += 1
    return "".join(out)


def split_outside_strings(s, sep=";"):
    parts, cur, q = [], [], None
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
            cur.append(ch)
            continue
        if ch == sep:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur))
    return parts


class ExprParser:
    def __init__(self, text):
        self.toks = tokenize(text)
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, kind=None):
        t = self.peek()
        if t is None:
            raise ValueError("Varatlan vege a kifejezesnek")
        if kind and t.kind != kind:
            raise ValueError(f"Vart {kind}, kapott {t}")
        self.i += 1
        return t

    def parse(self):
        if not self.toks:
            raise ValueError("Ures kifejezes")
        e = self.p_or()
        if self.i != len(self.toks):
            raise ValueError(f"Felesleges token: {self.toks[self.i:]}")
        return e

    def p_or(self):
        e = self.p_and()
        while (t := self.peek()) and (t.kind == "OR" or (t.kind == "IDENT" and t.value.upper() == "OR")):
            self.i += 1
            e = {"t": "bin", "op": "OR", "l": e, "r": self.p_and()}
        return e

    def p_and(self):
        e = self.p_not()
        while (t := self.peek()) and (t.kind == "AND" or (t.kind == "IDENT" and t.value.upper() == "AND")):
            self.i += 1
            e = {"t": "bin", "op": "AND", "l": e, "r": self.p_not()}
        return e

    def p_not(self):
        t = self.peek()
        if t and (t.kind == "NOT" or (t.kind == "IDENT" and t.value.upper() == "NOT")):
            self.i += 1
            return {"t": "un", "op": "NOT", "e": self.p_not()}
        return self.p_cmp()

    def p_cmp(self):
        e = self.p_add()
        while True:
            t = self.peek()
            if t is None:
                return e
            op = None
            if t.kind in ("EQ", "ASSIGN_EQ", "NE", "LE", "GE", "LE2", "GE2", "CONTAINS"):
                op = t.value.upper()
                if t.kind == "LE2":
                    op = "<"
                elif t.kind == "GE2":
                    op = ">"
                elif t.kind == "CONTAINS":
                    op = "$"
                self.i += 1
            elif t.kind == "IDENT" and t.value.upper() == "IN":
                # 'x IN ...' nem kell MVP-ben
                return e
            else:
                return e
            e = {"t": "bin", "op": op, "l": e, "r": self.p_add()}

    def p_add(self):
        e = self.p_mul()
        while (t := self.peek()) and t.kind in ("PLUS", "MINUS"):
            self.i += 1
            e = {"t": "bin", "op": "+" if t.kind == "PLUS" else "-", "l": e, "r": self.p_mul()}
        return e

    def p_mul(self):
        e = self.p_pow()
        while (t := self.peek()) and t.kind in ("STAR", "SLASH", "PERCENT"):
            self.i += 1
            op = {"STAR": "*", "SLASH": "/", "PERCENT": "%"}[t.kind]
            e = {"t": "bin", "op": op, "l": e, "r": self.p_pow()}
        return e

    def p_pow(self):
        e = self.p_unary()
        t = self.peek()
        if t and t.kind == "POWER":
            self.i += 1
            e = {"t": "bin", "op": "^", "l": e, "r": self.p_unary()}
        return e

    def p_unary(self):
        t = self.peek()
        if t and t.kind == "MINUS":
            self.i += 1
            return {"t": "un", "op": "NEG", "e": self.p_unary()}
        return self.p_atom()

    def p_atom(self):
        t = self.peek()
        if t is None:
            raise ValueError("Hianyzo operandus")
        if t.kind in ("STRING_DQ", "STRING_SQ"):
            self.i += 1
            q = t.value[0]
            inner = t.value[1:-1]
            return {"t": "lit", "v": inner}
        if t.kind == "DATE_LIT":
            self.i += 1
            return {"t": "lit", "v": t.value[2:-1], "date": True}
        if t.kind == "LOGICAL":
            self.i += 1
            v = t.value.upper()
            return {"t": "lit", "v": v in (".T.", ".Y.", ".TRUE.")}
        if t.kind == "NUMBER":
            self.i += 1
            return {"t": "lit", "v": float(t.value) if "." in t.value else int(t.value)}
        if t.kind == "LPAREN":
            self.i += 1
            e = self.p_or()
            self.eat("RPAREN")
            return e
        if t.kind == "IDENT":
            name = t.value.upper()
            self.i += 1
            # alias->mezo ?
            if (n := self.peek()) and n.kind == "ARROW":
                self.i += 1
                f = self.eat("IDENT").value.upper()
                return {"t": "field", "name": f, "alias": name}
            # fuggvenyhivas ?
            if (n := self.peek()) and n.kind == "LPAREN":
                self.i += 1
                args = []
                if (n2 := self.peek()) and n2.kind != "RPAREN":
                    while True:
                        args.append(self.p_or())
                        n3 = self.peek()
                        if n3 and n3.kind == "COMMA":
                            self.i += 1
                            continue
                        break
                self.eat("RPAREN")
                return {"t": "call", "name": name, "args": args}
            # NIL?
            if name == "NIL":
                return {"t": "lit", "v": None}
            return {"t": "var", "name": name}
        raise ValueError(f"Erthetetlen kifejezesresz: {t}")


def ex(text):
    return ExprParser(text.strip()).parse()


AT_RE = re.compile(r"^\s*@\s*(.+?)\s+SAY\s+(.+?)(?:\s+COLOR\s+(.+))?\s*$", re.I)
ATGET_RE = re.compile(r"^\s*@\s*(.+?)\s+GET\s+([A-Za-z_][A-Za-z0-9_]*)?(?:\s+PICTURE\s+(.+?))?(?:\s+COLOR\s+(.+))?\s*$", re.I)


class Program:
    def __init__(self, chunks):
        self.chunks = chunks  # [(lineno, text)]
        self.i = 0

    def peek(self):
        return self.chunks[self.i] if self.i < len(self.chunks) else None

    def next(self):
        c = self.peek()
        if c:
            self.i += 1
        return c

    @staticmethod
    def up(s):
        return s.strip().upper()


def parse_program(source):
    raw_lines = source.splitlines()
    logical = []
    buf, buf_no = "", 0
    for idx, raw in enumerate(raw_lines, 1):
        s = strip_line(raw).rstrip()
        st = s.strip()
        if not st or st.startswith("*") or st.upper().startswith(("NOTE", "REM ")):
            continue
        # folytatosor ';' veggel
        if st.endswith(";") and not st.upper().startswith("@"):
            buf += st[:-1] + " "
            if not buf_no:
                buf_no = idx
            continue
        full = (buf + st).strip()
        full_no = buf_no or idx
        buf, buf_no = "", 0
        if not full:
            continue
        for part in split_outside_strings(full, ";"):
            if part.strip():
                logical.append((full_no, part.strip()))
    if buf.strip():
        logical.append((buf_no, buf.strip()))
    p = Program(logical)
    stmts = parse_block(p, set())
    return stmts


def parse_block(p, ends):
    out = []
    while True:
        cur = p.peek()
        if cur is None:
            if ends:
                raise ValueError(f"Hianyzik lezaras: {ends}")
            return out
        no, text = cur
        u = text.upper()
        first = u.split()[0] if u.split() else ""
        # lezaro?
        for e in ends:
            if u == e or u.startswith(e + " ") or u.startswith(e + "("):
                return out
        # ELSE/ELSEIF/CASE/CATCH atadas a hivonak
        if first in ("ELSE", "OTHERWISE", "CATCH") or u.startswith("ELSEIF ") or u.startswith("ELSE IF ") or u.startswith("CASE ") or u == "CASE":
            return out
        p.next()
        out.append(parse_stmt(p, no, text))
    return out


def need(cond, msg):
    if not cond:
        raise ValueError(msg)


def parse_stmt(p, no, text):
    u = text.strip()
    uu = u.upper()

    # ---- @ SAY / @ GET ----
    if u.lstrip().startswith("@"):
        m = AT_RE.match(u)
        if m:
            rc, expr_s, col = m.group(1), m.group(2), m.group(3)
            r, c = parse_rc(rc)
            return {"t": "say", "line": no, "row": r, "col": c, "expr": ex(expr_s), "color": col}
        m2 = ATGET_RE.match(u)
        if m2:
            rc, var, pic, col = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
            r, c = parse_rc(rc)
            return {"t": "get", "line": no, "row": r, "col": c, "var": (var or "").upper(), "picture": pic}
        raise ValueError(f"{no}. sor: hibas @ utasitas: {u}")

    w = uu.split()
    k = w[0] if w else ""

    # ---- blokkok ----
    if k == "IF":
        cond = ex(u[2:].strip())
        then = parse_block(p, {"ELSE", "ENDIF", "ELSEIF"})
        branches = [{"cond": cond, "body": then}]
        els = []
        while True:
            cur = p.peek()
            if cur is None:
                raise ValueError("Hianyzik ENDIF")
            _, t2 = cur
            u2 = t2.strip().upper()
            if u2.startswith("ELSEIF ") or u2.startswith("ELSE IF "):
                p.next()
                expr_s = t2.strip()[7:] if u2.startswith("ELSEIF ") else t2.strip()[8:]
                branches.append({"cond": ex(expr_s), "body": parse_block(p, {"ELSE", "ENDIF", "ELSEIF"})})
                continue
            if u2 == "ELSE" or u2.startswith("ELSE "):
                p.next()
                els = parse_block(p, {"ENDIF"})
                cur2 = p.next()
                need(cur2 and cur2[1].strip().upper().startswith("ENDIF"), "Hianyzik ENDIF")
                break
            if u2.startswith("ENDIF"):
                p.next()
                break
            raise ValueError(f"Hibas IF szerkezet: {t2}")
        return {"t": "if", "line": no, "branches": branches, "else": els}

    if uu.startswith("DO WHILE"):
        cond = ex(u[8:].strip())
        body = parse_block(p, {"ENDDO", "END"})
        end = p.next()
        need(end, "Hianyzik ENDDO")
        return {"t": "dowhile", "line": no, "cond": cond, "body": body}

    if k == "WHILE":
        cond = ex(u[5:].strip())
        body = parse_block(p, {"ENDWHILE", "ENDDO", "END"})
        p.next()
        return {"t": "dowhile", "line": no, "cond": cond, "body": body}

    if k == "FOR":
        m = re.match(r"FOR\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s+TO\s+(.+?)(\s+STEP\s+(.+))?$", u, re.I)
        need(m, f"{no}. sor: hibas FOR: {u}")
        body = parse_block(p, {"NEXT", "ENDFOR"})
        p.next()
        step = ex(m.group(5)) if m.group(5) else {"t": "lit", "v": 1}
        return {"t": "for", "line": no, "var": m.group(1).upper(), "from": ex(m.group(2)), "to": ex(m.group(3)), "step": step, "body": body}

    if uu.startswith("DO CASE"):
        cases = []
        els = []
        while True:
            cur = p.peek()
            need(cur, "Hianyzik ENDCASE")
            _, t2 = cur
            u2 = t2.strip().upper()
            if u2.startswith("ENDCASE") or u2 == "END":
                p.next()
                break
            if u2.startswith("CASE "):
                p.next()
                cases.append({"cond": ex(t2.strip()[5:]), "body": parse_block(p, {"CASE", "OTHERWISE", "ENDCASE"})})
                continue
            if u2.startswith("OTHERWISE"):
                p.next()
                els = parse_block(p, {"ENDCASE"})
                continue
            raise ValueError(f"Hibas DO CASE: {t2}")
        return {"t": "docase", "line": no, "cases": cases, "else": els}

    if k in ("FUNCTION", "PROCEDURE"):
        m = re.match(r"(?:FUNCTION|PROCEDURE)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$", u, re.I)
        need(m, f"{no}. sor: hibas fuggvenyfej: {u}")
        args = [a.strip().upper() for a in (m.group(2) or "").split(",") if a.strip()]
        body = parse_block(p, {"RETURN"})
        # RETURN-t is beolvassuk, de nem kotelezo
        ret = None
        cur = p.peek()
        return {"t": "funcdef", "line": no, "name": m.group(1).upper(), "args": args, "body": body}

    if k == "TRY":
        body = parse_block(p, {"CATCH", "ENDTRY"})
        cur = p.peek()
        need(cur and cur[1].strip().upper().startswith("CATCH"), "Hianyzik CATCH")
        p.next()
        handler = parse_block(p, {"ENDTRY"})
        p.next()
        return {"t": "try", "line": no, "body": body, "handler": handler}

    # ---- egyszeru utasitasok ----
    if uu in ("READ",):
        return {"t": "read", "line": no}
    if uu.startswith("CLEAR"):
        return {"t": "clear", "line": no}
    if uu in ("CLS",):
        return {"t": "clear", "line": no}
    if uu in ("QUIT", "CANCEL"):
        return {"t": "quit", "line": no}
    if uu in ("EXIT",):
        return {"t": "exit", "line": no}
    if uu in ("LOOP",):
        return {"t": "loop", "line": no}
    if uu.startswith("RETURN"):
        rest = u[6:].strip()
        return {"t": "return", "line": no, "expr": ex(rest) if rest else None}
    if uu.startswith("?"):
        rest = u[1:].strip()
        if rest.startswith("?"):
            rest = rest[1:].strip()
        args = [ex(a) for a in split_outside_strings(rest, ",") if a.strip()] if rest else []
        return {"t": "qmark", "line": no, "args": args}
    if k in ("STORE",):
        m = re.match(r"STORE\s+(.+?)\s+TO\s+(.+)$", u, re.I)
        need(m, f"Hibas STORE: {u}")
        targets = [t.strip().upper() for t in split_outside_strings(m.group(2), ",")]
        return {"t": "store", "line": no, "expr": ex(m.group(1)), "targets": targets}
    if k in ("PUBLIC", "PRIVATE", "LOCAL", "MEMVAR"):
        rest = u.split(None, 1)[1] if len(u.split(None, 1)) > 1 else ""
        names = [t.strip().upper() for t in split_outside_strings(rest, ",") if t.strip()]
        return {"t": "declare", "line": no, "names": names}
    if uu.startswith("SET COLOR TO"):
        return {"t": "setcolor", "line": no, "color": u[12:].strip()}
    if uu.startswith("SET "):
        return {"t": "set", "line": no, "raw": u[4:].strip()}
    if uu.startswith("USE"):
        rest = u[3:].strip()
        if not rest:
            return {"t": "use", "line": no, "table": None}
        m = re.match(r"(.+?)(?:\s+ALIAS\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$", rest, re.I)
        return {"t": "use", "line": no, "table": m.group(1).strip(), "alias": (m.group(2) or "").upper() or None}
    if uu.startswith("SELECT "):
        return {"t": "select", "line": no, "which": u[7:].strip()}
    if uu.startswith("CLOSE"):
        return {"t": "close", "line": no, "raw": u[5:].strip()}
    if uu.startswith("CREATE "):
        m = re.match(r"CREATE\s+(?:TABLE\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*\((.+)\)\s*$", u, re.I | re.S)
        need(m, f"Hibas CREATE: {u} (pelda: CREATE vevok (nev C(30), kor N(3)))")
        return {"t": "create", "line": no, "table": m.group(1), "defs": m.group(2)}
    if uu.startswith("APPEND BLANK"):
        return {"t": "append", "line": no}
    if uu.startswith("REPLACE "):
        rest = u[8:].strip()
        pairs = []
        for part in split_outside_strings(rest, ","):
            m = re.match(r"([A-Za-z_][A-Za-z0-9_]*(?:->[A-Za-z_][A-Za-z0-9_]*)?)\s+WITH\s+(.+)$", part.strip(), re.I | re.S)
            need(m, f"Hibas REPLACE resz: {part}")
            pairs.append({"field": m.group(1).upper(), "expr": ex(m.group(2))})
        return {"t": "replace", "line": no, "pairs": pairs}
    if uu.startswith("SKIP"):
        rest = u[4:].strip()
        return {"t": "skip", "line": no, "n": ex(rest) if rest else {"t": "lit", "v": 1}}
    if uu.startswith("GO TOP") or uu == "GOTOP" or uu.startswith("GO TOP"):
        return {"t": "gotop", "line": no}
    if uu.startswith("GO BOTTOM") or uu.startswith("GOBOTTOM"):
        return {"t": "gobottom", "line": no}
    if re.match(r"^(GO|GOTO)\s+\d+\s*$", uu):
        n = int(uu.split()[1])
        return {"t": "goto", "line": no, "n": n}
    if re.match(r"^(GO|GOTO)\s+", uu):
        # GO TOP/BOTTOM mar lefedve; egyebkent kifejezes? rekord-sorszam
        rest = re.sub(r"^(GO|GOTO)\s+", "", u, flags=re.I).strip()
        if rest.upper() in ("TOP",):
            return {"t": "gotop", "line": no}
        if rest.upper() in ("BOTTOM",):
            return {"t": "gobottom", "line": no}
        return {"t": "gotoexpr", "line": no, "expr": ex(rest)}
    if uu.startswith("SEEK "):
        return {"t": "seek", "line": no, "expr": ex(u[5:].strip())}
    if uu.startswith("LOCATE FOR "):
        return {"t": "locate", "line": no, "cond": ex(u[11:].strip())}
    if uu.startswith("CONTINUE"):
        return {"t": "continue_find", "line": no}
    if uu.startswith("DELETE"):
        m = re.match(r"DELETE(?:\s+FOR\s+(.+))?$", u, re.I)
        return {"t": "delete", "line": no, "cond": ex(m.group(1)) if m.group(1) else None}
    if uu.startswith("RECALL"):
        return {"t": "recall", "line": no}
    if uu.startswith("PACK"):
        return {"t": "pack", "line": no}
    if uu.startswith("ZAP"):
        return {"t": "zap", "line": no}
    if uu.startswith("BROWSE"):
        return {"t": "browse", "line": no, "raw": u[6:].strip()}
    if uu.startswith("LIST") or uu.startswith("DISPLAY"):
        kw = "LIST" if uu.startswith("LIST") else "DISPLAY"
        rest = u[len(kw):].strip()
        return {"t": "list", "line": no, "raw": rest}
    if uu.startswith("INDEX ON "):
        m = re.match(r"INDEX\s+ON\s+(.+?)\s+TO\s+(.+)$", u, re.I)
        need(m, f"Hibas INDEX: {u}")
        return {"t": "index", "line": no, "expr": m.group(1), "tag": m.group(2)}
    if uu.startswith("MENU TO "):
        rest = u[8:].strip()
        return {"t": "menuto_old", "line": no, "var": rest.split()[0].upper(), "raw": rest}
    if uu.startswith("MENU "):
        m = re.match(r"MENU\s+(.+?)\s+TO\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+TITLE\s+(.+))?$", u, re.I)
        need(m, f"Hibas MENU: {u} (pelda: MENU \"a,b,c\" TO valasz TITLE \"cim\")")
        return {"t": "menu", "line": no, "options": ex(m.group(1)), "var": m.group(2).upper(), "title": m.group(3) or ""}
    if uu.startswith("SQL "):
        return {"t": "sql", "line": no, "expr": ex(u[4:].strip())}
    if uu.startswith("WAIT"):
        return {"t": "wait", "line": no, "raw": u[4:].strip()}
    if uu.startswith("ACCEPT"):
        m = re.match(r"ACCEPT\s*(?:TO\s+([A-Za-z_][A-Za-z0-9_]*))?(?:\s+PROMPT\s+(.+))?\s*$", u, re.I)
        need(m, f"Hibas ACCEPT: {u}")
        return {"t": "accept", "line": no, "var": (m.group(1) or "").upper() or None, "prompt": ex(m.group(2)) if m.group(2) else None}
    if uu.startswith("INPUT"):
        m = re.match(r"INPUT\s*(?:TO\s+([A-Za-z_][A-Za-z0-9_]*))?(?:\s+PROMPT\s+(.+))?\s*$", u, re.I)
        need(m, f"Hibas INPUT: {u}")
        return {"t": "input", "line": no, "var": (m.group(1) or "").upper() or None, "prompt": ex(m.group(2)) if m.group(2) else None}
    if uu.startswith("MSGBOX") or uu.startswith("MESSAGEBOX"):
        inner = re.sub(r"^(MSGBOX|MESSAGEBOX)\s*", "", u, flags=re.I)
        return {"t": "msgbox", "line": no, "expr": ex(inner.strip("() ")) if inner else {"t": "lit", "v": ""}}
    if uu.startswith("DO "):
        # DO fuggvenyhivas
        rest = u[3:].strip()
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*(?:WITH\s+(.+))?\s*$", rest, re.I | re.S)
        if m:
            args_s = m.group(2) if m.group(2) is not None else (m.group(3) or "")
            args = [ex(a) for a in split_outside_strings(args_s, ",") if a.strip()] if args_s.strip() else []
            return {"t": "docall", "line": no, "name": m.group(1).upper(), "args": args}
        raise ValueError(f"Hibas DO: {u}")

    # ertekadas: nev = expr  vagy nev := expr
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*(?:->[A-Za-z_][A-Za-z0-9_]*)?)\s*(=|:=)\s*(.+)$", u, re.S)
    if m and not re.match(r"^(IF|FOR|DO|WHILE)\b", uu):
        return {"t": "assign", "line": no, "target": m.group(1).upper(), "expr": ex(m.group(3))}

    # maganyos fuggvenyhivas sor: NEV(...)
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(.*\)\s*$", u, re.S)
    if m:
        e = ex(u)
        return {"t": "exprstmt", "line": no, "expr": e}

    raise ValueError(f"{no}. sor: ismeretlen utasitas: {u}")


def parse_rc(rc):
    parts = split_outside_strings(rc, ",")
    need(len(parts) == 2, f"Hibas sor,oszlop: {rc} (pelda: 5,10)")
    return ex(parts[0].strip()), ex(parts[1].strip())
