"""HxBase VM: AST / p-kod vegrehajto."""

import json
import urllib.request
from datetime import date, datetime

from .db import parse_field_defs


class RetExc(Exception):
    def __init__(self, value=None):
        self.value = value


class ExitExc(Exception):
    pass


class LoopExc(Exception):
    pass


class QuitExc(Exception):
    pass


def to_str(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return ".T." if v else ".F."
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def to_num(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if v is None or v == "":
        return 0
    try:
        return float(v) if isinstance(v, str) and "." in v else int(float(v)) if isinstance(v, str) else v
    except Exception:
        return 0


def is_true(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().upper()
        if s in ("", ".F.", "F", "N", ".N.", "0"):
            return False
        return True
    return bool(v)


class VM:
    def __init__(self, screen, dbman, base_dir="."):
        self.screen = screen
        self.db = dbman
        self.base_dir = base_dir
        self.mem = {}       # NEV -> ertek
        self.funcs = {}     # NEV -> funcdef node
        self.settings = {"DELETED": "OFF", "COLOR": "W/B"}
        self.locate_cond = None
        self.locate_pos = 0
        self.qmark_row = 0
        self.call_depth = 0

    # ---------- program ----------
    def run_code(self, stmts):
        # elso menet: fuggvenydefiniciok gyujtese
        main = []
        for s in stmts:
            if s.get("t") == "funcdef":
                self.funcs[s["name"].upper()] = s
            else:
                main.append(s)
        try:
            self.exec_list(main)
        except QuitExc:
            pass
        except RetExc:
            pass

    def exec_list(self, stmts):
        for s in stmts:
            self.exec(s)

    # ---------- utasitasok ----------
    def exec(self, s):
        t = s["t"]
        if t == "clear":
            self.screen.clear()
            self.qmark_row = 0
        elif t == "say":
            r = self.ev(s["row"])
            c = self.ev(s["col"])
            v = self.ev(s["expr"])
            self.screen.say(int(to_num(r)), int(to_num(c)), to_str(v), s.get("color"))
            self.qmark_row = max(self.qmark_row, int(to_num(r)) + 1)
        elif t == "get":
            self.screen.get(int(to_num(self.ev(s["row"]))), int(to_num(self.ev(s["col"]))), s["var"], s.get("picture"))
        elif t == "checkbox":
            pr = to_str(self.ev(s["prompt"])) if s.get("prompt") else s["var"]
            self.screen.checkbox(int(to_num(self.ev(s["row"]))), int(to_num(self.ev(s["col"]))), s["var"], pr)
        elif t == "radio":
            opts_v = self.ev(s["options"])
            if isinstance(opts_v, (list, tuple)):
                opts = [to_str(x) for x in opts_v]
            else:
                opts = [x.strip() for x in to_str(opts_v).split(",") if x.strip()]
            title = to_str(self.ev(s["title"])) if isinstance(s.get("title"), dict) else str(s.get("title") or "")
            self.screen.radio(int(to_num(self.ev(s["row"]))), int(to_num(self.ev(s["col"]))), s["var"], opts, title)
        elif t == "button":
            self.screen.button(int(to_num(self.ev(s["row"]))), int(to_num(self.ev(s["col"]))),
                               to_str(self.ev(s["label"])), s["action"])
        elif t == "read":
            self.screen.read(self.mem, self._button_action)
        elif t == "qmark":
            vals = [to_str(self.ev(a)) for a in s.get("args", [])]
            line = (" " if vals else "") + " ".join(vals)
            # ? uj sor, ?? folytatas — MVP: mindig uj sor a kovetkezo ures sorba
            self.screen.say(self.qmark_row, 0, line)
            self.screen.list_out(line)
            self.qmark_row += 1
        elif t == "assign":
            v = self.ev(s["expr"])
            self.store_target(s["target"], v)
        elif t == "store":
            v = self.ev(s["expr"])
            for tgt in s["targets"]:
                self.store_target(tgt, v)
        elif t == "declare":
            for n in s["names"]:
                self.mem.setdefault(n.upper(), "")
        elif t == "if":
            for br in s["branches"]:
                if is_true(self.ev(br["cond"])):
                    self.exec_list(br["body"])
                    break
            else:
                if s.get("else"):
                    self.exec_list(s["else"])
        elif t == "dowhile":
            while is_true(self.ev(s["cond"])):
                try:
                    self.exec_list(s["body"])
                except LoopExc:
                    continue
                except ExitExc:
                    break
        elif t == "for":
            start = to_num(self.ev(s["from"]))
            end = to_num(self.ev(s["to"]))
            step = to_num(self.ev(s["step"]))
            if step == 0:
                step = 1
            self.mem[s["var"]] = start
            i = start
            while (i <= end if step > 0 else i >= end):
                self.mem[s["var"]] = i
                try:
                    self.exec_list(s["body"])
                except LoopExc:
                    pass
                except ExitExc:
                    break
                i = to_num(self.mem[s["var"]]) + step
            self.mem[s["var"]] = i
        elif t == "docase":
            done = False
            for c in s["cases"]:
                if not done and is_true(self.ev(c["cond"])):
                    self.exec_list(c["body"])
                    done = True
                    break
            if not done and s.get("else"):
                self.exec_list(s["else"])
        elif t == "docall":
            self.call_func(s["name"], [self.ev(a) for a in s.get("args", [])])
        elif t == "exprstmt":
            self.ev(s["expr"])
        elif t == "funcdef":
            self.funcs[s["name"].upper()] = s
        elif t == "return":
            raise RetExc(self.ev(s["expr"]) if s.get("expr") is not None else None)
        elif t == "exit":
            raise ExitExc()
        elif t == "loop":
            raise LoopExc()
        elif t == "quit":
            raise QuitExc()
        elif t == "try":
            try:
                self.exec_list(s["body"])
            except QuitExc:
                raise
            except RetExc:
                raise
            except Exception as e:
                self.mem["ERROR"] = str(e)
                self.exec_list(s["handler"])
        elif t == "setcolor":
            self.settings["COLOR"] = s.get("color") or ""
        elif t == "set":
            self.do_set(s["raw"])
        elif t == "use":
            if s.get("table") is None:
                self.db.close_current()
            else:
                tbl = self.eval_table_name(s["table"])
                self.db.use(tbl, alias=s.get("alias"))
        elif t == "select":
            self.db.select(s["which"].strip().strip('"').strip("'"))
        elif t == "close":
            raw = (s.get("raw") or "").upper()
            if "ALL" in raw or "DATABASE" in raw or not raw.strip():
                self.db.close_all()
            else:
                self.db.close_current()
        elif t == "create":
            defs = parse_field_defs(s["defs"])
            tbl = self.eval_table_name(s["table"])
            self.db.create_table(tbl, defs)
            self.screen.list_out(f"Letrehozva: {tbl}")
        elif t == "append":
            self.need_table()
            self.db.cur().append_blank()
        elif t == "replace":
            self.need_table()
            for p in s["pairs"]:
                self.store_target(p["field"], self.ev(p["expr"]))
        elif t == "skip":
            self.need_table()
            self.db.cur().skip(int(to_num(self.ev(s["n"]))))
        elif t == "gotop":
            self.need_table()
            self.db.cur().go_top()
        elif t == "gobottom":
            self.need_table()
            self.db.cur().go_bottom()
        elif t == "goto":
            self.need_table()
            self.db.cur().go(int(s["n"]))
        elif t == "gotoexpr":
            self.need_table()
            self.db.cur().go(int(to_num(self.ev(s["expr"]))))
        elif t == "seek":
            self.do_seek(self.ev(s["expr"]))
        elif t == "locate":
            self.do_locate(s["cond"])
        elif t == "continue_find":
            self.do_continue()
        elif t == "sumavg":
            self.do_sumavg(s["op"], s["exprs"], s["targets"], s.get("cond"))
        elif t == "count":
            self.do_count(s["var"], s.get("cond"))
        elif t == "sort":
            self.do_sort(s["table"], s["key"], s.get("desc"), s.get("cond"))
        elif t == "copyto":
            self.do_copyto(s["file"], s.get("delimited"), s.get("fields"))
        elif t == "appendfrom":
            self.do_appendfrom(s["file"], s.get("delimited"))
        elif t == "delete":
            self.do_delete(s.get("cond"))
        elif t == "recall":
            self.need_table()
            area = self.db.cur()
            c = area.current()
            if c:
                area.recall_current()
        elif t == "pack":
            self.need_table()
            self.db.cur().pack()
        elif t == "zap":
            self.need_table()
            self.db.cur().zap()
        elif t == "browse":
            self.do_browse()
        elif t == "list":
            self.do_list(s.get("raw") or "")
        elif t == "index":
            self.do_index(s["expr"], s["tag"])
        elif t == "menu":
            opts_v = self.ev(s["options"])
            if isinstance(opts_v, (list, tuple)):
                opts = [to_str(x) for x in opts_v]
            else:
                opts = [x.strip() for x in to_str(opts_v).split(",") if x.strip()]
            title = to_str(self.ev(s["title"])) if isinstance(s.get("title"), dict) else str(s.get("title") or "")
            if isinstance(s.get("title"), dict):
                title = to_str(self.ev(s["title"]))
            choice = self.screen.menu(title, opts)
            self.mem[s["var"]] = choice
        elif t == "menuto_old":
            raise RuntimeError("Regi MENU TO nem tamogatott; hasznald: MENU \"a,b,c\" TO valasz")
        elif t == "sql":
            self.do_sql(to_str(self.ev(s["expr"])))
        elif t == "wait":
            raw = (s.get("raw") or "").strip()
            self.screen.wait(raw.strip('"').strip("'"))
        elif t == "accept":
            pr = to_str(self.ev(s["prompt"])) if s.get("prompt") else ""
            val = self.ask_text(pr, "")
            if s.get("var"):
                self.mem[s["var"]] = val
            else:
                self.mem["ACCEPT"] = val
        elif t == "input":
            pr = to_str(self.ev(s["prompt"])) if s.get("prompt") else ""
            val = self.ask_text(pr, "")
            # szamma alakitjuk ha lehet
            try:
                v = int(val)
            except Exception:
                try:
                    v = float(val)
                except Exception:
                    v = val
            if s.get("var"):
                self.mem[s["var"]] = v
            else:
                self.mem["ACCEPT"] = v
        elif t == "msgbox":
            self.screen.message(to_str(self.ev(s["expr"])))
        else:
            raise RuntimeError(f"Nem vegrehajthato: {t}")

    # ---------- segedek ----------
    def need_table(self):
        if self.db.cur() is None:
            raise RuntimeError("Nincs nyitott tabla (USE kell)")

    def eval_table_name(self, node_or_str):
        if isinstance(node_or_str, dict):
            if node_or_str.get("t") == "lit" and isinstance(node_or_str.get("v"), str):
                key = node_or_str["v"].upper()
                if key in self.mem and str(self.mem[key]).strip() != "":
                    return to_str(self.mem[key])
            return to_str(self.ev(node_or_str))
        return str(node_or_str).strip().strip('"').strip("'")

    def store_target(self, target, value):
        target = target.upper()
        if "->" in target:
            alias, field = target.split("->", 1)
            area = self.db.areas[self.db.alias_map[alias]] if alias in self.db.alias_map else None
            if area is None:
                raise RuntimeError(f"Nincs ilyen alias: {alias}")
            cur_alias = self.db.cur().alias if self.db.cur() else None
            # ideiglenes aliasvaltassal irunk
            idx = self.db.current
            self.db.current = self.db.alias_map[alias]
            try:
                self.db.set_field(field, value)
            finally:
                self.db.current = idx
            return
        # memvar vagy mezo?
        area = self.db.cur()
        cols = area.column_names() if area else []
        if target in self.mem or target not in cols:
            self.mem[target] = value
        else:
            self.db.set_field(target, value)

    def do_set(self, raw):
        u = raw.strip().upper()
        if u.startswith("FILTER TO"):
            cond_s = raw[9:].strip()
            area = self.db.cur()
            if area and (not cond_s or cond_s.upper() in ("", "OFF", ".F.")):
                area.filter_ast = None
            elif area:
                from .parser import ex as parse_ex
                area.filter_ast = parse_ex(cond_s)
            return
        if u.startswith("DELETED "):
            self.settings["DELETED"] = "ON" if "ON" in u else "OFF"
            return
        if u.startswith("DEFAULT TO") or u.startswith("DEFAULT "):
            return
        # egyeb SET: taroljuk
        self.settings[u.split()[0] if u.split() else ""] = raw

    def with_row(self, area, rowdict, fn):
        # sor mezok ideiglenes lathatosaga: eval soran field_value ezt a sort lassa
        old_order, old_pos = area.order, area.pos
        try:
            area.order = [(rowdict.get("_recno", 0), rowdict)]
            area.pos = 0
            return fn()
        finally:
            area.order, area.pos = old_order, old_pos
            area._update_flags()

    def row_visible(self, area, row):
        if self.settings.get("DELETED") == "ON" and row.get("_deleted"):
            return False
        if area.filter_ast is not None:
            try:
                return is_true(self.with_row(area, row, lambda: self.ev(area.filter_ast)))
            except Exception:
                return False
        return True

    def do_locate(self, cond):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        self.locate_cond = cond
        self.locate_pos = 0
        for i, (recno, row) in enumerate(area.order):
            if self.row_visible(area, row) and is_true(self.with_row(area, row, lambda: self.ev(cond))):
                area.pos = i
                area._update_flags()
                self.locate_pos = i + 1
                return
        area.pos = len(area.order)
        area.eof = True
        self.locate_pos = len(area.order)

    def do_continue(self):
        self.need_table()
        area = self.db.cur()
        if self.locate_cond is None:
            raise RuntimeError("CONTINUE LOCATE nelkul")
        for i in range(self.locate_pos, len(area.order)):
            recno, row = area.order[i]
            if self.row_visible(area, row) and is_true(self.with_row(area, row, lambda: self.ev(self.locate_cond))):
                area.pos = i
                area._update_flags()
                self.locate_pos = i + 1
                return
        area.pos = len(area.order)
        area.eof = True

    def _button_action(self, action_node):
        """BUTTON ACTION hivasa (GUI kattintasbol)."""
        if isinstance(action_node, dict) and action_node.get("t") == "call":
            self.call_func(action_node["name"], [self.ev(x) for x in action_node.get("args", [])])
        elif action_node is not None:
            self.ev(action_node)

    def _iter_visible(self, area, cond):
        for _, row in area.order:
            if not self.row_visible(area, row):
                continue
            if cond is not None and not is_true(self.with_row(area, row, lambda: self.ev(cond))):
                continue
            yield row

    def do_sumavg(self, op, exprs, targets, cond):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        sums = [0.0] * len(exprs)
        n = 0
        for row in self._iter_visible(area, cond):
            n += 1
            for i, e in enumerate(exprs):
                if i < len(sums):
                    sums[i] += to_num(self.with_row(area, row, lambda: self.ev(e)))
        for i, tgt in enumerate(targets):
            v = sums[i] if i < len(sums) else 0.0
            if op == "AVERAGE" and n:
                v = v / n
            self.mem[tgt] = v
        if len(targets) < len(sums):
            for i in range(len(targets), len(sums)):
                v = sums[i] / n if (op == "AVERAGE" and n) else sums[i]
                self.screen.list_out(f"{op}({i + 1}) = {to_str(v)}")

    def do_count(self, var, cond):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        self.mem[var] = sum(1 for _ in self._iter_visible(area, cond))

    def do_sort(self, table_node, key, desc, cond):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        tbl = self.eval_table_name(table_node)
        keyed = []
        for row in self._iter_visible(area, cond):
            keyed.append((self.with_row(area, row, lambda: self.ev(key)), row))
        try:
            keyed.sort(key=lambda p: (p[0] is None, p[0]), reverse=bool(desc))
        except TypeError:
            keyed.sort(key=lambda p: to_str(p[0]), reverse=bool(desc))
        defs = [(f[0], f[1], f[2], f[3]) for f in area.fields]
        self.db.create_table(tbl, defs)
        import sqlite3 as _sq
        db_path = self.db._resolve(tbl)
        conn = _sq.connect(db_path)
        cols = area.column_names()
        for _, row in keyed:
            vals = [row.get(c) for c in cols]
            conn.execute(f'INSERT INTO "{tbl}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({", ".join("?" * len(cols))})', vals)
        conn.commit()
        conn.close()
        self.screen.list_out(f"SORT: {len(keyed)} sor -> {tbl}")

    def do_copyto(self, file_node, delimited, fields_raw):
        import csv
        self.need_table()
        area = self.db.cur()
        area.refresh()
        fname = to_str(self.ev(file_node)) if isinstance(file_node, dict) else str(file_node)
        if delimited and "." not in fname.split("/")[-1].split("\\")[-1]:
            fname += ".csv"
        import os
        if not os.path.isabs(fname):
            fname = os.path.join(self.base_dir, fname)
        cols = area.column_names()
        with open(fname, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for row in self._iter_visible(area, None):
                w.writerow([row.get(c) if row.get(c) is not None else "" for c in cols])
        self.screen.list_out(f"COPY TO {fname}")

    def do_appendfrom(self, file_node, delimited):
        import csv
        import os
        self.need_table()
        area = self.db.cur()
        fname = to_str(self.ev(file_node)) if isinstance(file_node, dict) else str(file_node)
        if not os.path.isabs(fname):
            cand = os.path.join(self.base_dir, fname)
            if os.path.exists(cand):
                fname = cand
        cols = area.column_names()
        n = 0
        with open(fname, encoding="utf-8", newline="") as f:
            for rec in csv.DictReader(f):
                area.append_blank()
                for c in cols:
                    if c in rec and rec[c] != "":
                        try:
                            area.replace(c, rec[c])
                        except Exception:
                            pass
                n += 1
        area.refresh()
        self.screen.list_out(f"APPEND FROM {fname}: {n} sor")

    def do_delete(self, cond):
        self.need_table()
        area = self.db.cur()
        if cond is None:
            c = area.current()
            if c:
                area.delete_current()
            return
        for recno, row in list(area.order):
            if self.with_row(area, row, lambda: self.ev(cond)):
                area.conn.execute(f'UPDATE "{area.table}" SET _deleted=1 WHERE _recno=?', (row["_recno"],))
        area.conn.commit()

    def do_seek(self, val):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        target = to_str(val).strip().upper()
        cols = area.column_names()
        for i, (recno, row) in enumerate(area.order):
            for c in cols:
                if to_str(row.get(c)).strip().upper() == target or to_str(row.get(c)).strip().upper().startswith(target):
                    area.pos = i
                    area._update_flags()
                    return
        area.pos = len(area.order)
        area.eof = True

    def do_browse(self):
        self.need_table()
        area = self.db.cur()
        area.refresh()
        cols = area.column_names()
        rows = []
        for _, row in area.order:
            if self.row_visible(area, row):
                rows.append([row.get(c) for c in cols])
        widths = [f[2] if len(f) > 2 else 10 for f in area.fields] or None
        lcols = {f[0] for f in area.fields if f[1] == "L"}
        rows = [[(bool(v) if c in lcols and v is not None else v) for c, v in zip(cols, r)] for r in rows]
        self.screen.browse(area.alias, cols, rows, widths)

    def do_list(self, raw):
        from .screen import format_table
        self.need_table()
        area = self.db.cur()
        area.refresh()
        cols = area.column_names()
        cond = None
        if raw.strip():
            import re
            m = re.match(r"(?:FIELDS\s+.+?\s+)?FOR\s+(.+)$", raw.strip(), re.I)
            if m:
                from .parser import ex as parse_ex
                cond = parse_ex(m.group(1))
        data = []
        for _, row in area.order:
            if not self.row_visible(area, row):
                continue
            if cond is not None and not is_true(self.with_row(area, row, lambda: self.ev(cond))):
                continue
            data.append([row.get(c) for c in cols])
        widths = [f[2] if len(f) > 2 else 10 for f in area.fields] or None
        lcols = {f[0] for f in area.fields if f[1] == "L"}
        data = [[(bool(v) if c in lcols and v is not None else v) for c, v in zip(cols, r)] for r in data]
        for line in format_table(cols, data, widths):
            self.screen.list_out(line)
            self.screen.say(self.qmark_row, 0, line)
            self.qmark_row += 1

    def do_index(self, expr_s, tag):
        self.need_table()
        area = self.db.cur()
        col = str(expr_s).strip().upper()
        # ha AST-dict jon string helyett (parser igy adja), probaljuk kinyerni
        if isinstance(expr_s, dict):
            if expr_s.get("t") == "var":
                col = expr_s["name"]
            else:
                self.screen.list_out("INDEX: osszetett kifejezes — logikai index, fizikai nem keszult")
                return
        if col in area.column_names():
            idx = f"ix_{area.table}_{col}".lower()
            area.conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{area.table}"("{col}")')
            area.conn.commit()
            self.screen.list_out(f"Index kesz: {col}")
        else:
            self.screen.list_out("INDEX: nem mezonev, kihagyva")

    def do_sql(self, q):
        self.need_table()
        area = self.db.cur()
        cur = area.conn.execute(q)
        if q.strip().upper().startswith("SELECT"):
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            self.screen.browse("SQL", cols, [list(r) for r in rows])
            self.screen.list_out(f"SQL: {len(rows)} sor")
        else:
            area.conn.commit()
            self.screen.list_out("SQL OK")

    def ask_text(self, prompt, default):
        if prompt:
            self.screen.list_out(prompt)
        # headless teszt-input
        if hasattr(self.screen, "inputs") and self.screen.inputs:
            return next(iter(self.screen.inputs.values()))
        try:
            if type(self.screen).__name__ == "GuiScreen":
                from tkinter import simpledialog
                try:
                    return simpledialog.askstring("HxBase", prompt or "Add meg:", initialvalue=str(default)) or ""
                except Exception:
                    return ""
            return input((prompt or "Add meg: ") + " ")
        except EOFError:
            return ""

    def call_func(self, name, args):
        name = name.upper()
        if name in self.funcs:
            fn = self.funcs[name]
            saved = dict(self.mem)
            try:
                for i, a in enumerate(fn.get("args", [])):
                    self.mem[a] = args[i] if i < len(args) else ""
                try:
                    self.exec_list(fn["body"])
                except RetExc as r:
                    return r.value
                return None
            finally:
                # args torlese, egyeb memvar megmarad (Clipper PUBLIC-szeru)
                for a in fn.get("args", []):
                    self.mem.pop(a, None)
                for k, v in saved.items():
                    if k not in self.mem or k not in fn.get("args", []):
                        pass
                # egyszerusitve: globalis mem marad, csak mentett args all vissza
                for a in fn.get("args", []):
                    if a in saved:
                        self.mem[a] = saved[a]
            return None
        return self.call_builtin(name, args)

    # ---------- kifejezesek ----------
    def ev(self, e):
        t = e["t"]
        if t == "lit":
            return e["v"]
        if t == "var":
            n = e["name"]
            if n in self.mem:
                return self.mem[n]
            # mezo?
            area = self.db.cur()
            if area and n in area.column_names():
                return self.db.field_value(n)
            if n in ("EOF",):
                a = self.db.cur()
                return a.eof if a else True
            if n in ("BOF",):
                a = self.db.cur()
                return a.bof if a else True
            raise RuntimeError(f"Ismeretlen valtozo/mezo: {n}")
        if t == "field":
            return self.db.field_value(e["name"], alias=e.get("alias"))
        if t == "un":
            v = self.ev(e["e"])
            if e["op"] == "NOT":
                return not is_true(v)
            if e["op"] == "NEG":
                return -to_num(v)
            raise RuntimeError(f"Ismeretlen unaris op: {e['op']}")
        if t == "bin":
            return self.ev_bin(e["op"], self.ev(e["l"]), self.ev(e["r"]))
        if t == "call":
            return self.call_func(e["name"], [self.ev(a) for a in e.get("args", [])])
        raise RuntimeError(f"Ismeretlen kifejezes: {t}")

    def ev_bin(self, op, l, r):
        if op in ("AND", "OR"):
            return (is_true(l) and is_true(r)) if op == "AND" else (is_true(l) or is_true(r))
        if op == "$":
            return to_str(r).upper().find(to_str(l).upper()) >= 0 or to_str(l).upper() in to_str(r).upper()
        if op in ("=", "=="):
            if isinstance(l, bool) or isinstance(r, bool):
                return is_true(l) == is_true(r)
            if isinstance(l, (int, float)) and isinstance(r, (int, float)):
                return l == r
            return to_str(l).strip().upper() == to_str(r).strip().upper() if isinstance(l, str) or isinstance(r, str) else l == r
        if op in ("<>", "!=", "#"):
            return not self.ev_bin("=", l, r)
        if op in ("<", ">", "<=", ">="):
            try:
                ln, rn = float(l), float(r)
                return {"<": ln < rn, ">": ln > rn, "<=": ln <= rn, ">=": ln >= rn}[op]
            except Exception:
                ls, rs = to_str(l).upper(), to_str(r).upper()
                return {"<": ls < rs, ">": ls > rs, "<=": ls <= rs, ">=": ls >= rs}[op]
        if op == "+":
            if isinstance(l, str) or isinstance(r, str):
                return to_str(l) + to_str(r)
            return to_num(l) + to_num(r)
        if op == "-":
            return to_num(l) - to_num(r)
        if op == "*":
            return to_num(l) * to_num(r)
        if op == "/":
            d = to_num(r)
            if d == 0:
                raise RuntimeError("Nullaval osztas")
            return to_num(l) / d
        if op == "%":
            return to_num(l) % to_num(r)
        if op == "^":
            return to_num(l) ** to_num(r)
        raise RuntimeError(f"Ismeretlen operator: {op}")

    # ---------- beepitett fuggvenyek ----------
    def call_builtin(self, name, args):
        a = args
        if name in ("UPPER",):
            return to_str(a[0] if a else "").upper()
        if name in ("LOWER",):
            return to_str(a[0] if a else "").lower()
        if name in ("ALLTRIM", "TRIM"):
            return to_str(a[0] if a else "").strip()
        if name in ("LTRIM",):
            return to_str(a[0] if a else "").lstrip()
        if name in ("RTRIM",):
            return to_str(a[0] if a else "").rstrip()
        if name in ("LEN", "LENNUM"):
            return len(to_str(a[0] if a else ""))
        if name in ("SUBSTR", "SUBS"):
            s = to_str(a[0] if len(a) > 0 else "")
            start = int(to_num(a[1] if len(a) > 1 else 1)) - 1
            n = int(to_num(a[2] if len(a) > 2 else len(s)))
            return s[start:start + n]
        if name in ("LEFT",):
            return to_str(a[0]).lstrip()[:int(to_num(a[1]))] if len(a) > 1 else to_str(a[0])
        if name in ("RIGHT",):
            n = int(to_num(a[1])) if len(a) > 1 else 0
            return to_str(a[0])[(-n):] if n else ""
        if name in ("AT",):
            return to_str(a[1]).upper().find(to_str(a[0]).upper()) + 1 if len(a) > 1 else 0
        if name in ("STR",):
            v = to_num(a[0]) if a else 0
            w = int(to_num(a[1])) if len(a) > 1 else 0
            d = int(to_num(a[2])) if len(a) > 2 else 0
            s = f"{v:.{d}f}" if d else str(int(round(v)) if float(v).is_integer() else v)
            return s.rjust(w) if w else s
        if name in ("VAL",):
            try:
                return int(to_str(a[0]).strip()) if to_str(a[0]).strip().lstrip("-").isdigit() else float(to_str(a[0]).strip() or 0)
            except Exception:
                return 0
        if name in ("CHR",):
            return chr(int(to_num(a[0]))) if a else ""
        if name in ("ASC",):
            s = to_str(a[0] if a else "")
            return ord(s[0]) if s else 0
        if name in ("DATE",):
            return date.today().isoformat()
        if name in ("TIME",):
            return datetime.now().strftime("%H:%M:%S")
        if name in ("YEAR", "MONTH", "DAY"):
            s = to_str(a[0] if a else "")
            try:
                d = date.fromisoformat(s[:10])
                return {"YEAR": d.year, "MONTH": d.month, "DAY": d.day}[name]
            except Exception:
                return 0
        if name in ("DTOC",):
            return to_str(a[0] if a else "")
        if name in ("CTOD",):
            return to_str(a[0] if a else "")
        if name in ("IIF",):
            return a[1] if len(a) > 1 and is_true(a[0]) else (a[2] if len(a) > 2 else None)
        if name in ("EMPTY",):
            v = a[0] if a else None
            return v is None or v == "" or v == 0 or v is False
        if name in ("EOF",):
            cur = self.db.cur()
            return cur.eof if cur else True
        if name in ("BOF",):
            cur = self.db.cur()
            return cur.bof if cur else True
        if name in ("RECNO", "RECN"):
            cur = self.db.cur()
            return cur.recno() if cur else 0
        if name in ("RECCOUNT", "LASTREC"):
            cur = self.db.cur()
            return cur.reccount() if cur else 0
        if name in ("DELETED",):
            cur = self.db.cur()
            c = cur.current() if cur else None
            return bool(c.get("_deleted")) if c else False
        if name in ("ALIAS",):
            cur = self.db.cur()
            return cur.alias if cur else ""
        if name in ("INT",):
            return int(to_num(a[0] if a else 0))
        if name in ("ROUND",):
            return round(float(to_num(a[0] if a else 0)), int(to_num(a[1] if len(a) > 1 else 0)))
        if name in ("ABS",):
            return abs(to_num(a[0] if a else 0))
        if name in ("MIN", "MAX"):
            nums = [to_num(x) for x in a]
            return (min if name == "MIN" else max)(nums) if nums else 0
        if name in ("MSGBOX", "MESSAGEBOX"):
            self.screen.message(to_str(a[0] if a else ""), to_str(a[1] if len(a) > 1 else ""))
            return 1
        if name in ("JSONSTRING", "JSONENCODE"):
            return json.dumps(a[0] if a else None, ensure_ascii=False)
        if name in ("JSONPARSE", "JSONDECODE"):
            try:
                return json.loads(to_str(a[0] if a else ""))
            except Exception as e:
                raise RuntimeError(f"JSON hiba: {e}")
        if name in ("HTTPGET",):
            url = to_str(a[0] if a else "")
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    return r.read().decode("utf-8", "replace")
            except Exception as e:
                raise RuntimeError(f"HTTP hiba: {e}")
        if name in ("FILE",):
            import os
            return os.path.exists(to_str(a[0] if a else ""))
        if name in ("REPLICATE",):
            s = to_str(a[0] if a else "")
            return s * max(0, int(to_num(a[1]) if len(a) > 1 else 0))
        if name in ("SPACE",):
            return " " * max(0, int(to_num(a[0]) if a else 0))
        if name in ("PADL", "PADR", "PADC"):
            s = to_str(a[0] if a else "")
            ln = int(to_num(a[1]) if len(a) > 1 else 0)
            pad = to_str(a[2])[:1] if len(a) > 2 and to_str(a[2]) else " "
            if len(s) >= ln:
                return s[:ln]
            if name == "PADL":
                return s.rjust(ln, pad)
            if name == "PADR":
                return s.ljust(ln, pad)
            return s.center(ln, pad)
        if name in ("STUFF",):
            s = to_str(a[0] if a else "")
            start = max(1, int(to_num(a[1]) if len(a) > 1 else 1)) - 1
            ndel = max(0, int(to_num(a[2]) if len(a) > 2 else 0))
            ins = to_str(a[3]) if len(a) > 3 else ""
            return s[:start] + ins + s[start + ndel:]
        if name in ("RAT",):
            sub = to_str(a[0] if a else "").upper()
            s = to_str(a[1] if len(a) > 1 else "").upper()
            return s.rfind(sub) + 1
        if name in ("TRANSFORM",):
            v = a[0] if a else ""
            pic = to_str(a[1]).upper() if len(a) > 1 else ""
            if "B" in pic and to_num(v) == 0:
                return ""
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return to_str(v)
            dec = 0
            if "." in pic:
                dec = sum(1 for ch in pic.split(".", 1)[1] if ch in "90#")
            s = f"{float(v):,.{dec}f}"
            if "$" in pic:
                s = "$" + s
            return s
        if name in ("DTOS",):
            return to_str(a[0] if a else "").replace("-", "")[:8]
        if name in ("VALTYPE", "TYPE"):
            v = a[0] if a else None
            if v is None:
                return "U"
            if isinstance(v, bool):
                return "L"
            if isinstance(v, (int, float)):
                return "N"
            if isinstance(v, str):
                return "C"
            if isinstance(v, (list, tuple)):
                return "A"
            return "H"
        if name in ("FCOUNT",):
            cur = self.db.cur()
            return len(cur.column_names()) if cur else 0
        if name in ("FIELDNAME", "FIELD"):
            cur = self.db.cur()
            cols = cur.column_names() if cur else []
            i = int(to_num(a[0] if a else 0)) - 1
            return cols[i] if 0 <= i < len(cols) else ""
        if name in ("DBFNAME", "DBF", "ALIASNAME"):
            cur = self.db.cur()
            return (cur.db_path if cur else "")
        if name in ("INKEY", "LASTKEY"):
            return 0
        raise RuntimeError(f"Ismeretlen fuggveny: {name}")
