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


def _stdin_is_tty():
    import sys as _s
    try:
        return _s.stdin.isatty()
    except Exception:
        return False


def _get_key():
    """Egy billentyu nyers olvasasa (terminal-elozmeny nelkul).
    Vissza: 'Up','Down','Left','Right','Home','End','Tab','ShiftTab',
    'Return','Escape','BackSpace','space' vagy a leutott karakter.
    None: nem interaktiv stdin (pipe) vagy hiba."""
    import sys as _s
    if not _stdin_is_tty():
        return None
    try:
        import msvcrt
    except ImportError:
        return _get_key_posix()
    try:
        ch = msvcrt.getwch()
    except Exception:
        return None
    if ch in ("\x00", "\xe0"):
        try:
            ch2 = msvcrt.getwch()
        except Exception:
            return None
        return {"H": "Up", "P": "Down", "K": "Left", "M": "Right",
                "G": "Home", "O": "End", "R": "Insert", "S": "Delete",
                "I": "PgUp", "Q": "PgDn"}.get(ch2, "")
    if ch == "\x03":
        raise KeyboardInterrupt()
    if ch == "\r":
        return "Return"
    if ch == "\t":
        return "Tab"
    if ch == "\x0f":
        return "ShiftTab"
    if ch == "\x1b":
        return "Escape"
    if ch == "\x08":
        return "BackSpace"
    if ch == " ":
        return "space"
    return ch


def _get_key_posix():
    import sys as _s
    import select as _sel
    try:
        import tty as _tty
        import termios as _tm
    except ImportError:
        return None
    fd = _s.stdin.fileno()
    try:
        old = _tm.tcgetattr(fd)
    except Exception:
        return None
    try:
        _tty.setraw(fd)
        ch = _s.stdin.read(1)
        if ch == "\x1b":
            seq = ""
            while True:
                r, _, _ = _sel.select([_s.stdin], [], [], 0.05)
                if not r:
                    break
                seq += _s.stdin.read(1)
            return {"[A": "Up", "[B": "Down", "[C": "Right", "[D": "Left",
                    "[H": "Home", "[F": "End", "[Z": "ShiftTab",
                    "OP": "F1", "OQ": "F2"}.get(seq, "Escape")
        if ch in ("\r", "\n"):
            return "Return"
        if ch == "\t":
            return "Tab"
        if ch == "\x7f":
            return "BackSpace"
        if ch == "\x03":
            raise KeyboardInterrupt()
        if ch == " ":
            return "space"
        return ch
    except KeyboardInterrupt:
        raise
    except Exception:
        return None
    finally:
        try:
            _tm.tcsetattr(fd, _tm.TCSADRAIN, old)
        except Exception:
            pass


def _hide_cursor():
    import sys as _s
    try:
        _s.stdout.write("\x1b[?25l")
        _s.stdout.flush()
    except Exception:
        pass


def _show_cursor():
    import sys as _s
    try:
        _s.stdout.write("\x1b[?25h")
        _s.stdout.flush()
    except Exception:
        pass


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
        # Csak caption (SAY) nem fokuszalhato: GET, CHECKBOX, RADIO, BUTTON igen.
        entries = self.pending_gets
        self.pending_gets = []
        if not entries:
            return
        focus = [g for g in entries if g.get("kind", "get") in ("get", "checkbox", "radio", "button")]
        if not _stdin_is_tty():
            self._read_piped(memvars, action_fn, focus)
            return
        self._read_keys(memvars, action_fn, focus)

    def _dialog_content(self, g, edits):
        kind = g.get("kind", "get")
        if kind == "get":
            return "%s: [%s]" % (g["var"], str(edits.get(g["var"], ""))[:18])
        if kind == "checkbox":
            return "[%s] %s" % ("X" if edits.get(g["var"], False) else " ", g.get("prompt") or g["var"])
        if kind == "radio":
            opts = g.get("options") or []
            try:
                ch = int(edits.get(g["var"], 1) or 1)
            except Exception:
                ch = 1
            cur = opts[ch - 1] if 1 <= ch <= len(opts) else "?"
            return "%s: < %s >" % (g.get("title") or g["var"], cur)
        return "[ %s ]" % g.get("label")

    def _draw_dialog(self, focus, edits, cur_idx, title, hint):
        texts = [self._dialog_content(g, edits) for g in focus]
        r1, c1, r2, c2, w = self._dialog_geom(texts)
        saved = self.save_region(r1, c1, r2, c2)
        self.draw_box(r1, c1, r2, c2, title)
        for i, g in enumerate(focus):
            t = texts[i][:w - 4].ljust(w - 4)
            if i == cur_idx:
                self._put(r1 + 2 + i, c1 + 2, t, "black", "white")
            else:
                self._put(r1 + 2 + i, c1 + 2, t, "white", "black")
        self._put(r2 - 1, c1 + max(1, (w - len(hint)) // 2), hint[:w - 2], "black", "white")
        self._render()
        return saved, r1, c1, r2, c2, w

    def _read_piped(self, memvars, action_fn, focus):
        # Nem interaktiv stdin (pipe): soronkenti bekeres, ahogy eddig.
        pre = {}
        for g in focus:
            var = g.get("var")
            if var:
                pre[var] = memvars.get(var.upper(), "")
        texts = [self._dialog_content(g, pre) for g in focus]
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

    def _read_keys(self, memvars, action_fn, focus):
        # Nyers billentyuk: nincs terminal-echo, nincs elozmeny. TAB vegigsetal
        # a mezokon es gombokon (caption kivetel mindenen).
        import sys as _sys
        edits, poses = {}, {}
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                edits[var] = str(memvars.get(var.upper(), ""))[:18]
                poses[var] = len(edits[var])
            elif kind == "checkbox":
                edits[var] = bool(memvars.get(var.upper(), False))
            elif kind == "radio":
                try:
                    ch = int(memvars.get(var.upper(), 1) or 1)
                except Exception:
                    ch = 1
                opts = g.get("options") or []
                edits[var] = max(1, min(ch, len(opts) or 1))
        hint = "Tab: mezok  Enter: OK  ^W: kesz  Esc: megse"
        saved, r1, c1, r2, c2, w = self._draw_dialog(focus, edits, 0, "Adatbevitel", hint)
        cur = {"i": 0}
        had = set(memvars.keys())
        snap = dict(memvars)

        def _flush():
            for g in focus:
                kind = g.get("kind", "get")
                var = g.get("var")
                if kind == "get":
                    memvars[var.upper()] = HeadlessScreen._apply_picture(edits[var], g.get("picture"))
                elif kind in ("checkbox", "radio"):
                    memvars[var.upper()] = edits[var]

        def render():
            texts = [self._dialog_content(g, edits) for g in focus]
            for i, t in enumerate(texts):
                t = t[:w - 4].ljust(w - 4)
                if i == cur["i"]:
                    self._put(r1 + 2 + i, c1 + 2, t, "black", "white")
                else:
                    self._put(r1 + 2 + i, c1 + 2, t, "white", "black")
            self._put(r2 - 1, c1 + max(1, (w - len(hint)) // 2), hint[:w - 2], "black", "white")
            self._render()
            g = focus[cur["i"]]
            if g.get("kind", "get") == "get":
                var = g["var"]
                pos = min(poses[var], 18, len(edits[var]))
                grow = r1 + 2 + cur["i"] + 1
                gcol = c1 + 2 + len(var) + 3 + pos + 1
                _sys.stdout.write("\x1b[%d;%dH\x1b[?25h" % (grow, gcol))
            else:
                _sys.stdout.write("\x1b[?25l")
            _sys.stdout.flush()

        def finish(save):
            if save:
                _flush()
            else:
                for k in [k for k in memvars.keys() if k not in had]:
                    del memvars[k]
                memvars.update(snap)
            self.restore_region(saved)
            self._render()
            _show_cursor()

        _hide_cursor()
        render()
        n = len(focus)
        try:
            while True:
                try:
                    k = _get_key()
                except KeyboardInterrupt:
                    finish(False)
                    raise
                if k is None or k == "":
                    continue
                g = focus[cur["i"]]
                kind = g.get("kind", "get")
                var = g.get("var")
                if k in ("Tab", "Down"):
                    cur["i"] = (cur["i"] + 1) % n
                elif k in ("ShiftTab", "Up"):
                    cur["i"] = (cur["i"] - 1) % n
                elif k == "Escape":
                    finish(False)
                    return
                elif k == "\x17":
                    # Ctrl+W: Clipper-modra kesz (OK) barhonnan
                    finish(True)
                    return
                elif k == "Return":
                    if kind == "button":
                        _flush()
                        if action_fn is not None:
                            try:
                                action_fn(g.get("action"))
                            except Exception as e:
                                memvars["ERROR"] = str(e)
                        cur["i"] = (cur["i"] + 1) % n
                    elif kind == "checkbox":
                        edits[var] = not edits[var]
                    elif kind == "radio":
                        opts = g.get("options") or []
                        edits[var] = edits[var] % (len(opts) or 1) + 1
                    elif cur["i"] == n - 1:
                        finish(True)
                        return
                    else:
                        cur["i"] += 1
                elif k == "space":
                    if kind == "checkbox":
                        edits[var] = not edits[var]
                    elif kind == "radio":
                        opts = g.get("options") or []
                        edits[var] = edits[var] % (len(opts) or 1) + 1
                    elif kind == "get":
                        t = edits[var]
                        p = poses[var]
                        if len(t) < 18:
                            edits[var] = t[:p] + " " + t[p:]
                            poses[var] = p + 1
                elif k == "BackSpace":
                    if kind == "get":
                        p = poses[var]
                        if p > 0:
                            t = edits[var]
                            edits[var] = t[:p - 1] + t[p:]
                            poses[var] = p - 1
                elif k == "Left":
                    if kind == "get":
                        poses[var] = max(0, poses[var] - 1)
                    elif kind == "radio":
                        opts = g.get("options") or []
                        edits[var] = (edits[var] - 2) % (len(opts) or 1) + 1
                    else:
                        cur["i"] = (cur["i"] - 1) % n
                elif k == "Right":
                    if kind == "get":
                        poses[var] = min(len(edits[var]), poses[var] + 1)
                    elif kind == "radio":
                        opts = g.get("options") or []
                        edits[var] = edits[var] % (len(opts) or 1) + 1
                    else:
                        cur["i"] = (cur["i"] + 1) % n
                elif k == "Home":
                    if kind == "get":
                        poses[var] = 0
                elif k == "End":
                    if kind == "get":
                        poses[var] = len(edits[var])
                elif kind == "get" and len(k) == 1 and k.isprintable():
                    t = edits[var]
                    p = poses[var]
                    if len(t) < 18:
                        edits[var] = t[:p] + k + t[p:]
                        poses[var] = p + 1
                elif kind == "radio" and k.isdigit():
                    opts = g.get("options") or []
                    if k != "0" and int(k) <= len(opts):
                        edits[var] = int(k)
                _flush()
                render()
        finally:
            _show_cursor()

    def _wait_key(self, prompt=""):
        # Nyers billentyuvaras (nincs echo, nincs elozmeny); pipe eseten Enter.
        if not _stdin_is_tty():
            if prompt:
                try:
                    input(prompt)
                except EOFError:
                    pass
            return ""
        _hide_cursor()
        if prompt:
            import sys as _s
            _s.stdout.write(prompt)
            _s.stdout.flush()
        try:
            while True:
                try:
                    k = _get_key()
                except KeyboardInterrupt:
                    return "Escape"
                if k is None or k == "":
                    continue
                return k
        finally:
            _show_cursor()

    def _input_line(self, prompt, initial=""):
        # Sorecho billentyunkent, terminal-elozmeny nelkul.
        import sys as _s
        if not _stdin_is_tty():
            try:
                _s.stdout.write(prompt)
                _s.stdout.flush()
                return input()
            except EOFError:
                return ""
        _s.stdout.write(prompt)
        _s.stdout.flush()
        buf = list(initial)
        _s.stdout.write("".join(buf))
        _s.stdout.flush()
        _show_cursor()
        try:
            while True:
                try:
                    k = _get_key()
                except KeyboardInterrupt:
                    _s.stdout.write("\n")
                    return initial
                if k is None or k == "":
                    continue
                if k in ("Return",):
                    _s.stdout.write("\n")
                    return "".join(buf)
                if k == "Escape":
                    _s.stdout.write("\n")
                    return initial
                if k == "BackSpace":
                    if buf:
                        buf.pop()
                        _s.stdout.write("\b \b")
                        _s.stdout.flush()
                    continue
                if len(k) == 1 and k.isprintable():
                    if len(buf) < 60:
                        buf.append(k)
                        _s.stdout.write(k)
                        _s.stdout.flush()
        finally:
            _hide_cursor()

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
        self._wait_key()
        self.restore_region(saved)
        self._render()

    def menu(self, title, options):
        # Lenyilo ablak a racsra, hattermentessel. Nyilak/Enter vagy sorszam.
        self.menus.append((title, options))
        if not options:
            return 0
        opts = [str(o) for o in options]
        numbered = ["%d. %s" % (i + 1, o) for i, o in enumerate(opts)]
        r1, c1, r2, c2, w = self._dialog_geom(numbered + [str(title or "")])
        saved = self.save_region(r1, c1, r2, c2)
        self.draw_box(r1, c1, r2, c2, str(title or "Menu"))
        sel = {"i": 0}

        def render():
            for i, t in enumerate(numbered):
                t = ("> " + t if i == sel["i"] else "  " + t)[:w - 4].ljust(w - 4)
                if i == sel["i"]:
                    self._put(r1 + 2 + i, c1 + 2, t, "black", "white")
                else:
                    self._put(r1 + 2 + i, c1 + 2, t, "white", "black")
            self._render()

        if not _stdin_is_tty():
            render()
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
        render()
        try:
            while True:
                try:
                    k = self._wait_key()
                except KeyboardInterrupt:
                    k = "Escape"
                if k in ("Up", "Left"):
                    sel["i"] = (sel["i"] - 1) % len(opts)
                    render()
                elif k in ("Down", "Right", "Tab", "space"):
                    sel["i"] = (sel["i"] + 1) % len(opts)
                    render()
                elif k in ("Return",):
                    ch = sel["i"] + 1
                    break
                elif k == "Escape":
                    ch = 0
                    break
                elif isinstance(k, str) and k.isdigit() and k != "0" and int(k) <= len(opts):
                    ch = int(k)
                    break
        finally:
            self.restore_region(saved)
            self._render()
        return ch

    def wait(self, msg=""):
        super().wait(msg)
        if msg:
            print(msg)
        self._wait_key("...billi...")

    def browse(self, alias, columns, rows, widths=None):
        # Csak szoveg: igazitott tablazat, laponkent szunettel (nyers billentyu).
        super().browse(alias, columns, rows, widths)
        import sys as _sys
        lines = format_table(columns, rows, widths)
        tty = _sys.stdin.isatty()
        for i, ln in enumerate(lines):
            print(ln)
            if tty and (i + 1) % 20 == 0 and i + 1 < len(lines):
                k = self._wait_key("-- tovabb (barmi), vege (Q): ")
                if isinstance(k, str) and k.strip().upper() == "Q":
                    break

    def prompt_user(self, text):
        if text:
            print(text)
        return self._input_line("> ", "")

    def close(self):
        self._render()
