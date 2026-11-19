"""HxBase screen: kvazi-grafikus GUI-grid (Tkinter) + headless valtozat teszthez."""

ROW_COUNT = 25
COL_COUNT = 80


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return ".T." if v else ".F."
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def format_table(columns, rows, widths=None, max_col=30):
    """Clipper-BROWSE szeru igazitas: fejlec es mezok azonos szelesseggel, monospace-hez."""
    cols = [str(c) for c in columns]
    strs = [[_cell(v) for v in r] for r in rows]
    w = []
    for i, c in enumerate(cols):
        mx = len(c)
        if widths and i < len(widths) and widths[i]:
            mx = max(mx, min(int(widths[i]), max_col))
        for r in strs:
            if i < len(r):
                mx = max(mx, min(len(r[i]), max_col))
        w.append(max(1, min(mx, max_col)))

    def fmt_row(r):
        cells = []
        for i in range(len(cols)):
            v = r[i] if i < len(r) else ""
            if len(v) > w[i]:
                v = v[:w[i]]
            cells.append(v.ljust(w[i]))
        return "  ".join(cells).rstrip()

    return [fmt_row(cols), "  ".join("-" * x for x in w)] + [fmt_row(r) for r in strs]


def parse_color(spec, default_fg="white", default_bg="black"):
    """Clipper 'W/B,R/B' stilus: 'FG/BG'. Vissza: (fg, bg)."""
    if not spec:
        return default_fg, default_bg
    s = spec.strip().strip('"').strip("'").upper()
    # csak elso tag kell
    first = s.split()[0].split(",")[0]
    if "/" in first:
        fg, bg = first.split("/", 1)
        return _map(fg.strip() or default_fg), _map(bg.strip() or default_bg)
    return _map(first or default_fg), default_bg


def _map(c):
    table = {
        "W": "white", "WHITE": "white",
        "B": "black", "BLACK": "black",
        "R": "red", "RED": "red",
        "G": "green", "GREEN": "green",
        "B+": "blue", "BLUE": "blue", "BG": "blue",
        "Y": "yellow", "YELLOW": "yellow",
        "GR": "gray", "GRAY": "gray", "GREY": "gray",
        "N": "black", "": "white",
    }
    return table.get(c.strip().upper(), "white")


class HeadlessScreen:
    """GUI nelkuli kepernyo: buffer + GET-lista. Teszthez es --headless modhoz."""

    def __init__(self, rows=ROW_COUNT, cols=COL_COUNT):
        self.rows = rows
        self.cols = cols
        self.buf = [[" "] * cols for _ in range(rows)]
        self.colors = [[("white", "black")] * cols for _ in range(rows)]
        self.pending_gets = []  # list of dict(row,col,var,picture)
        self.messages = []
        self.menus = []
        self.browses = []
        self.lists = []
        self.inputs = {}  # varname.upper() -> value (elore beadott teszt-input)

    def clear(self):
        self.buf = [[" "] * self.cols for _ in range(self.rows)]
        self.colors = [[("white", "black")] * self.cols for _ in range(self.rows)]
        self.pending_gets = []

    def scroll_up(self, n=1):
        for _ in range(n):
            self.buf.pop(0)
            self.buf.append([" "] * self.cols)
            self.colors.pop(0)
            self.colors.append([("white", "black")] * self.cols)

    def say(self, row, col, text, color=None):
        fg, bg = parse_color(color) if color else ("white", "black")
        r = int(row)
        if r >= self.rows:
            self.scroll_up(r - self.rows + 1)
            r = self.rows - 1
        r = max(0, r)
        c = max(0, min(self.cols - 1, int(col)))
        for i, ch in enumerate(str(text)):
            if c + i >= self.cols:
                break
            self.buf[r][c + i] = ch
            self.colors[r][c + i] = (fg, bg)

    def get(self, row, col, varname, picture=None):
        self.pending_gets.append({"kind": "get", "row": row, "col": col, "var": varname, "picture": picture})

    def checkbox(self, row, col, varname, prompt=""):
        self.pending_gets.append({"kind": "checkbox", "row": row, "col": col, "var": varname, "prompt": prompt})

    def radio(self, row, col, varname, options, title=""):
        self.pending_gets.append({"kind": "radio", "row": row, "col": col, "var": varname,
                                 "options": options, "title": title})

    def button(self, row, col, label, action):
        self.pending_gets.append({"kind": "button", "row": row, "col": col, "label": label, "action": action})

    @staticmethod
    def _apply_picture(value, picture):
        if picture and isinstance(value, str) and "!" in picture.upper():
            return value.upper()
        return value

    def read(self, memvars, action_fn=None):
        # headless: elore beadott inputs vagy ures string; kepre is kirajzoljuk
        for g in self.pending_gets:
            kind = g.get("kind", "get")
            if kind == "get":
                v = self.inputs.get(g["var"].upper(), memvars.get(g["var"].upper(), ""))
                v = self._apply_picture(v, g.get("picture"))
                memvars[g["var"].upper()] = v
                self.say(g["row"], g["col"], str(v))
            elif kind == "checkbox":
                raw = self.inputs.get(g["var"].upper(), memvars.get(g["var"].upper(), False))
                v = raw if isinstance(raw, bool) else (str(raw).strip().upper() in (".T.", "T", "Y", "1", "IGEN", "I", "TRUE"))
                memvars[g["var"].upper()] = v
                self.say(g["row"], g["col"], ("[X] " if v else "[ ] ") + str(g.get("prompt") or g["var"]))
            elif kind == "radio":
                opts = g.get("options") or []
                raw = self.inputs.get(g["var"].upper(), memvars.get(g["var"].upper(), 1))
                try:
                    v = int(raw)
                except Exception:
                    v = next((i + 1 for i, o in enumerate(opts) if str(o).strip().upper() == str(raw).strip().upper()), 1)
                v = max(1, min(v, len(opts) or 1))
                memvars[g["var"].upper()] = v
                txt = " / ".join(("[%s] %s" % ("X" if i + 1 == v else " ", o)) for i, o in enumerate(opts))
                self.say(g["row"], g["col"], (str(g.get("title")) + ": " if g.get("title") else "") + txt)
            elif kind == "button":
                self.say(g["row"], g["col"], "[ %s ]" % g.get("label"))
                self.list_out("BUTTON: %s (headless modban nem kattinthato)" % g.get("label"))
        self.pending_gets = []

    def text_row(self, r):
        return "".join(self.buf[r]).rstrip()

    def dump(self):
        return "\n".join(self.text_row(r) for r in range(self.rows) if self.text_row(r).strip())

    # magasabb szintu API-k a VM-nek
    def message(self, text, title=""):
        self.messages.append((title, text))

    def menu(self, title, options):
        self.menus.append((title, options))
        # headless: elso opcio
        return 1 if options else 0

    def browse(self, alias, columns, rows, widths=None):
        self.browses.append((alias, columns, rows))
        for line in format_table(columns, rows, widths):
            self.list_out(line)

    # --- DOS-os ablak-emulacio: hattermentes / keret / visszaallitas ---
    def save_region(self, r1, c1, r2, c2):
        r1 = max(0, r1); c1 = max(0, c1)
        r2 = min(self.rows - 1, r2); c2 = min(self.cols - 1, c2)
        return {"r1": r1, "c1": c1,
                "cells": [list(row[c1:c2 + 1]) for row in self.buf[r1:r2 + 1]],
                "colors": [list(row[c1:c2 + 1]) for row in self.colors[r1:r2 + 1]]}

    def restore_region(self, saved):
        for i, row in enumerate(saved["cells"]):
            r = saved["r1"] + i
            self.buf[r][saved["c1"]:saved["c1"] + len(row)] = row
        for i, row in enumerate(saved["colors"]):
            r = saved["r1"] + i
            self.colors[r][saved["c1"]:saved["c1"] + len(row)] = row

    def _put(self, r, c, text, fg="black", bg="white"):
        for i, ch in enumerate(str(text)):
            if 0 <= r < self.rows and 0 <= c + i < self.cols:
                self.buf[r][c + i] = ch
                self.colors[r][c + i] = (fg, bg)

    def prompt_user(self, text):
        if text:
            self.list_out(text)
        try:
            return input((text or "Add meg: ") + " ")
        except EOFError:
            return ""

    def draw_box(self, r1, c1, r2, c2, title=""):
        r1 = max(0, r1); c1 = max(0, c1)
        r2 = min(self.rows - 1, r2); c2 = min(self.cols - 1, c2)
        w = c2 - c1 + 1
        top = "+" + "-" * (w - 2) + "+"
        bot = "+" + "-" * (w - 2) + "+"
        for i, ch in enumerate(top):
            self.buf[r1][c1 + i] = ch
        for i, ch in enumerate(bot):
            self.buf[r2][c1 + i] = ch
        for r in range(r1 + 1, r2):
            self.buf[r][c1] = "|"
            self.buf[r][c2] = "|"
            for cc in range(c1 + 1, c2):
                self.buf[r][cc] = " "
        if title:
            t = " " + str(title)[:w - 4] + " "
            for i, ch in enumerate(t):
                self.buf[r1][c1 + 2 + i] = ch

    def list_out(self, text):
        self.lists.append(text)

    def wait(self, msg=""):
        self.messages.append(("", msg))

    def close(self):
        pass


class ConsoleScreen(HeadlessScreen):
    """Valodi szoveges konzol: 80x25-os racs ANSI-val a terminalra. Semmi GUI."""

    _FG = {"black": 30, "red": 31, "green": 32, "yellow": 33, "blue": 34,
           "white": 37, "gray": 90, "grey": 90}
    _BG = {"black": 40, "red": 41, "green": 42, "yellow": 43, "blue": 44,
           "white": 47, "gray": 100, "grey": 100}

    def __init__(self, rows=ROW_COUNT, cols=COL_COUNT):
        super().__init__(rows, cols)
        try:
            import os as _os
            _os.system("")  # VT-mod bekapcsolasa Windows konzolon
        except Exception:
            pass
        self._need_clear = True

    @classmethod
    def _ansi(cls, fg, bg):
        return "\x1b[%d;%dm" % (cls._FG.get(str(fg).lower(), 37),
                               cls._BG.get(str(bg).lower(), 40))

    def _render(self):
        import sys as _sys
        out = []
        if self._need_clear:
            out.append("\x1b[2J")
            self._need_clear = False
        out.append("\x1b[H")
        for r in range(self.rows):
            cur = None
            for c in range(self.cols):
                fb = self.colors[r][c]
                if fb != cur:
                    out.append(self._ansi(*fb))
                    cur = fb
                out.append(self.buf[r][c])
            out.append("\x1b[0m")
            if r < self.rows - 1:
                out.append("\n")
        _sys.stdout.write("".join(out))
        _sys.stdout.flush()

    def clear(self):
        super().clear()
        self._need_clear = True
        self._render()

    def say(self, row, col, text, color=None):
        super().say(row, col, text, color)
        self._render()

    def _dialog_geom(self, lines):
        w = min(max([len(t) for t in lines] + [20]) + 6, self.cols - 4)
        h = len(lines) + 5
        r1 = max(0, (self.rows - h) // 2)
        c1 = max(0, (self.cols - w) // 2)
        return r1, c1, r1 + h - 1, c1 + w - 1, w

    def read(self, memvars, action_fn=None):
        # DOS-mod: hattermentes -> keretes dialog a racsra -> adatbekeres -> visszaallitas.
        entries = self.pending_gets
        self.pending_gets = []
        if not entries:
            return
        focus = [g for g in entries if g.get("kind", "get") in ("get", "checkbox", "radio", "button")]

        def content(g):
            kind = g.get("kind", "get")
            if kind == "get":
                return "%s: [%s]" % (g["var"], str(memvars.get(g["var"].upper(), ""))[:18])
            if kind == "checkbox":
                return "[%s] %s" % ("X" if memvars.get(g["var"].upper(), False) else " ",
                                    g.get("prompt") or g["var"])
            if kind == "radio":
                opts = g.get("options") or []
                try:
                    ch = int(memvars.get(g["var"].upper(), 1) or 1)
                except Exception:
                    ch = 1
                cur = opts[ch - 1] if 1 <= ch <= len(opts) else "?"
                return "%s: < %s >" % (g.get("title") or g["var"], cur)
            return "[ %s ]" % g.get("label")

        texts = [content(g) for g in focus]
        r1, c1, r2, c2, w = self._dialog_geom(texts)
        saved = self.save_region(r1, c1, r2, c2)
        self.draw_box(r1, c1, r2, c2, "Adatbevitel")
        for i, t in enumerate(texts):
            self._put(r1 + 2 + i, c1 + 2, t[:w - 4].ljust(w - 4), "white", "black")
        hint = "ures sor = marad"
        self._put(r2 - 1, c1 + max(1, (w - len(hint)) // 2), hint[:w - 2], "black", "white")
        self._render()
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                cur = str(memvars.get(var.upper(), ""))
                try:
                    ans = input("%s [%s]: " % (var, cur))
                except EOFError:
                    ans = ""
                memvars[var.upper()] = HeadlessScreen._apply_picture(ans, g.get("picture")) if ans != "" else cur
            elif kind == "checkbox":
                cur = bool(memvars.get(var.upper(), False))
                try:
                    ans = input("%s (I/N) [%s]: " % (g.get("prompt") or var, "I" if cur else "N"))
                except EOFError:
                    ans = ""
                if ans.strip() == "":
                    memvars[var.upper()] = cur
                else:
                    memvars[var.upper()] = ans.strip().upper() in ("I", "IGEN", "Y", "1", ".T.", "T")
            elif kind == "radio":
                opts = g.get("options") or []
                for i, o in enumerate(opts, 1):
                    print("  %d. %s" % (i, o))
                try:
                    cur = memvars.get(var.upper(), 1)
                    ans = input("%s [1-%d, most: %s]: " % (g.get("title") or var, len(opts), cur))
                except EOFError:
                    ans = ""
                if ans.strip().isdigit() and 1 <= int(ans.strip()) <= len(opts):
                    memvars[var.upper()] = int(ans.strip())
                else:
                    memvars[var.upper()] = cur
            elif kind == "button":
                try:
                    ans = input("[ %s ] futtat? (I/N) [N]: " % g.get("label"))
                except EOFError:
                    ans = ""
                if ans.strip().upper() in ("I", "IGEN", "Y", "1") and action_fn is not None:
                    try:
                        action_fn(g.get("action"))
                    except Exception as e:
                        memvars["ERROR"] = str(e)
        self.restore_region(saved)
        self._render()

    def message(self, text, title=""):
        super().message(text, title)
        lines = str(text).splitlines() or [""]
        r1, c1, r2, c2, w = self._dialog_geom(lines + [str(title or "")])
        saved = self.save_region(r1, c1, r2, c2)
        self.draw_box(r1, c1, r2, c2, str(title or "HxBase"))
        for i, ln in enumerate(lines):
            self._put(r1 + 2 + i, c1 + 3, ln[:w - 6], "white", "black")
        ok = "[ OK - Enter ]"
        self._put(r1 + 2 + len(lines), c1 + 2, ok.ljust(w - 4), "black", "white")
        self._render()
        try:
            input()
        except EOFError:
            pass
        self.restore_region(saved)
        self._render()

    def menu(self, title, options):
        # Lenyilo ablak a racsra, hattermentessel. Sorszam beirasa valaszt.
        self.menus.append((title, options))
        if not options:
            return 0
        opts = [str(o) for o in options]
        numbered = ["%d. %s" % (i + 1, o) for i, o in enumerate(opts)]
        r1, c1, r2, c2, w = self._dialog_geom(numbered + [str(title or "")])
        saved = self.save_region(r1, c1, r2, c2)
        self.draw_box(r1, c1, r2, c2, str(title or "Menu"))
        for i, t in enumerate(numbered):
            self._put(r1 + 2 + i, c1 + 2, t[:w - 4].ljust(w - 4), "white", "black")
        self._render()
        while True:
            try:
                ans = input("Valasz [1-%d, ures = 1]: " % len(opts))
            except EOFError:
                ans = ""
            if ans.strip() == "":
                ch = 1
                break
            if ans.strip().isdigit() and 1 <= int(ans.strip()) <= len(opts):
                ch = int(ans.strip())
                break
            print("1 es %d kozotti szamot adj meg." % len(opts))
        self.restore_region(saved)
        self._render()
        return ch

    def wait(self, msg=""):
        super().wait(msg)
        if msg:
            print(msg)
        try:
            input("...Enter...")
        except EOFError:
            pass

    def browse(self, alias, columns, rows, widths=None):
        # Csak szoveg: igazitott tablazat, laponkent szunettel.
        super().browse(alias, columns, rows, widths)
        import sys as _sys
        lines = format_table(columns, rows, widths)
        tty = _sys.stdin.isatty()
        for i, ln in enumerate(lines):
            print(ln)
            if tty and (i + 1) % 20 == 0 and i + 1 < len(lines):
                try:
                    more = input("-- tovabb (Enter), vege (Q): ")
                except EOFError:
                    break
                if more.strip().upper() == "Q":
                    break

    def prompt_user(self, text):
        if text:
            print(text)
        try:
            return input("> ")
        except EOFError:
            return ""

    def close(self):
        self._render()
