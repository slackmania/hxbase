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
                if ans != "":
                    memvars[var.upper()] = HeadlessScreen._apply_picture(ans, g.get("picture"))
            elif kind == "checkbox":
                cur = bool(memvars.get(var.upper(), False))
                try:
                    ans = input("%s (I/N) [%s]: " % (g.get("prompt") or var, "I" if cur else "N"))
                except EOFError:
                    ans = ""
                if ans.strip() != "":
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
