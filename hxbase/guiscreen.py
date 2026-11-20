"""HxBase GUIClipper: rendes GUI frontend ugyanahhoz a nyelvhez/VM-hez.

Ugyanazok a .prg-k futnak valtoztatas nelkul, csak valodi GUI widgeteken:
READ = urlap (Entry/Checkbutton/Radiobutton/Button), MENU = Listbox,
MSGBOX = uzenetablak, BROWSE = tablazat (Treeview), ACCEPT/INPUT = bekerodialoogus.
Racsméretek: 80x25 (eredeti), 130x32 (kiterjesztett), 155x48 (extrem).
"""

from .screen import HeadlessScreen, parse_color

MODES = {
    "80x25": (80, 25),
    "130x32": (130, 32),
    "155x48": (155, 48),
}


def parse_grid(spec):
    """'130x32' -> (cols, rows). Ismeretlenre 80x25."""
    import re as _re
    m = _re.match(r"^\s*(\d{2,3})\s*[xX]\s*(\d{2,3})\s*$", str(spec or ""))
    if m:
        c, r = max(40, min(int(m.group(1)), 200)), max(10, min(int(m.group(2)), 60))
        return c, r
    key = str(spec or "").strip()
    return MODES.get(key, MODES["80x25"])


_TK_COLORS = {
    "white": "white", "black": "black", "red": "red",
    "green": "green", "blue": "blue", "yellow": "yellow",
    "gray": "gray", "grey": "gray",
}


def _tkc(name, default):
    return _TK_COLORS.get(str(name or "").lower(), default)


class GuiScreen(HeadlessScreen):
    """Tkinter ablak: szines karakterracs + valodi widgetek."""

    def __init__(self, grid="80x25"):
        cols, rows = parse_grid(grid)
        super().__init__(rows, cols)
        self.grid_spec = "%dx%d" % (cols, rows)
        import tkinter as tk
        from tkinter import font as tkfont
        self._tk = tk
        self.root = tk.Tk()  # kijelzo nelkul TclError -> hivo fallbackol
        self.root.title("HxBase GUIClipper %s" % self.grid_spec)
        self.root.configure(bg="black")
        size = 11
        self.font = tkfont.Font(family="Consolas", size=size)
        if "Consolas" not in self.font.actual("family"):
            self.font = tkfont.Font(family="Courier New", size=size)
        while size > 6:
            wpx = self.font.measure("M") * cols + 24
            hpx = self.font.metrics("linespace") * rows + 24
            try:
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            except Exception:
                break
            if wpx <= sw - 40 and hpx <= sh - 100:
                break
            size -= 1
            self.font.configure(size=size)
        self.text = tk.Text(self.root, width=cols, height=rows, bg="black", fg="white",
                            font=self.font, insertbackground="white", wrap="none",
                            state="disabled", borderwidth=0, highlightthickness=0)
        self.text.pack(fill="both", expand=True)
        self._tags = set()
        self._closed = False
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._closed = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def _tag(self, fg, bg):
        name = "c_%s_%s" % (fg, bg)
        if name not in self._tags:
            try:
                self.text.tag_config(name, foreground=_tkc(fg, "white"),
                                     background=_tkc(bg, "black"))
            except Exception:
                pass
            self._tags.add(name)
        return name

    def _refresh(self):
        if self._closed:
            return
        try:
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            for r in range(self.rows):
                for c in range(self.cols):
                    fg, bg = self.colors[r][c]
                    self.text.insert("end", self.buf[r][c], self._tag(fg, bg))
                if r < self.rows - 1:
                    self.text.insert("end", "\n")
            self.text.configure(state="disabled")
            self.root.update_idletasks()
        except Exception:
            pass

    def clear(self):
        super().clear()
        self._refresh()

    def say(self, row, col, text, color=None):
        super().say(row, col, text, color)
        self._refresh()

    # ---------- READ: valodi urlap ----------
    def read(self, memvars, action_fn=None):
        entries = self.pending_gets
        self.pending_gets = []
        if not entries:
            return
        if self._closed:
            return super().read(memvars, action_fn)
        import tkinter as tk
        focus = [g for g in entries if g.get("kind", "get") in ("get", "checkbox", "radio", "button")]
        snap = dict(memvars)
        win = tk.Toplevel(self.root)
        win.title("Adatbevitel")
        win.configure(bg="#f0f0f0")
        try:
            win.transient(self.root)
        except Exception:
            pass
        vars_ = {}
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                fr = tk.Frame(win, bg="#f0f0f0")
                fr.pack(fill="x", padx=8, pady=2)
                tk.Label(fr, text="%s:" % var, bg="#f0f0f0", font=self.font, width=12,
                         anchor="w").pack(side="left")
                sv = tk.StringVar(value=str(memvars.get(var.upper(), "")))
                tk.Entry(fr, textvariable=sv, font=self.font, width=30).pack(side="left", padx=6)
                vars_[var.upper()] = ("get", sv, g.get("picture"))
            elif kind == "checkbox":
                bv = tk.BooleanVar(value=bool(memvars.get(var.upper(), False)))
                tk.Checkbutton(win, text=str(g.get("prompt") or var), variable=bv,
                               bg="#f0f0f0", font=self.font, anchor="w").pack(fill="x", padx=8, pady=2)
                vars_[var.upper()] = ("checkbox", bv, None)
            elif kind == "radio":
                opts = g.get("options") or []
                lf = tk.LabelFrame(win, text=str(g.get("title") or var), bg="#f0f0f0", font=self.font)
                lf.pack(fill="x", padx=8, pady=4)
                iv = tk.IntVar(value=int(memvars.get(var.upper(), 1) or 1))
                for i, o in enumerate(opts, 1):
                    tk.Radiobutton(lf, text=str(o), value=i, variable=iv,
                                   bg="#f0f0f0", font=self.font, anchor="w").pack(fill="x", padx=12)
                vars_[var.upper()] = ("radio", iv, None)
            elif kind == "button":
                act = g.get("action")

                def _fire(a=act):
                    try:
                        if action_fn is not None:
                            action_fn(a)
                    except Exception as e:
                        memvars["ERROR"] = str(e)
                    self._refresh()

                tk.Button(win, text=str(g.get("label")), command=_fire,
                          font=self.font).pack(padx=8, pady=3)
        done = {"ok": False}

        def _ok(_=None):
            for k, (kind, v, pic) in vars_.items():
                try:
                    val = v.get()
                    if kind == "get":
                        val = HeadlessScreen._apply_picture(val, pic)
                    memvars[k] = val
                except Exception:
                    pass
            self._paint_read(focus, memvars)
            done["ok"] = True
            win.destroy()

        def _cancel(_=None):
            for k in [k for k in memvars.keys() if k not in snap]:
                del memvars[k]
            memvars.update(snap)
            win.destroy()

        btns = tk.Frame(win, bg="#f0f0f0")
        btns.pack(pady=6)
        tk.Button(btns, text="OK (Enter)", command=_ok, font=self.font).pack(side="left", padx=6)
        tk.Button(btns, text="Megse (Esc)", command=_cancel, font=self.font).pack(side="left", padx=6)
        win.bind("<Return>", _ok)
        win.bind("<Escape>", _cancel)
        win.protocol("WM_DELETE_WINDOW", _cancel)
        try:
            self.root.wait_window(win)
        except Exception:
            pass

    def _paint_read(self, focus, memvars):
        # bevitt ertekek a racsra is (mint a DOS-os READ)
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                self.say(g["row"], g["col"], str(memvars.get(var.upper(), "")))
            elif kind == "checkbox":
                v = bool(memvars.get(var.upper(), False))
                self.say(g["row"], g["col"], ("[X] " if v else "[ ] ") + str(g.get("prompt") or var))
            elif kind == "radio":
                opts = g.get("options") or []
                try:
                    ch = int(memvars.get(var.upper(), 1) or 1)
                except Exception:
                    ch = 1
                cur = opts[ch - 1] if 1 <= ch <= len(opts) else "?"
                self.say(g["row"], g["col"], "%s: < %s >" % (g.get("title") or var, cur))
            elif kind == "button":
                self.say(g["row"], g["col"], "[ %s ]" % g.get("label"))

    # ---------- MENU: Listbox ----------
    def menu(self, title, options):
        self.menus.append((title, options))
        if self._closed or not options:
            return 1 if options else 0
        import tkinter as tk
        opts = [str(o) for o in options]
        win = tk.Toplevel(self.root)
        win.title(str(title or "Menu"))
        try:
            win.transient(self.root)
        except Exception:
            pass
        tk.Label(win, text=str(title or "Valassz:"), font=self.font).pack(padx=10, pady=6)
        lb = tk.Listbox(win, font=self.font, width=min(60, max([len(o) for o in opts] + [20])),
                        height=min(16, len(opts)))
        for o in opts:
            lb.insert("end", o)
        lb.pack(padx=10, pady=4)
        lb.select_set(0)
        lb.focus_set()
        choice = {"v": 0}

        def _ok(_=None):
            try:
                sel = lb.curselection()
                choice["v"] = (sel[0] + 1) if sel else 0
            except Exception:
                choice["v"] = 0
            win.destroy()

        def _cancel(_=None):
            choice["v"] = 0
            win.destroy()

        tk.Button(win, text="OK", command=_ok, font=self.font).pack(pady=4)
        lb.bind("<Double-Button-1>", _ok)
        win.bind("<Return>", _ok)
        win.bind("<Escape>", _cancel)
        win.protocol("WM_DELETE_WINDOW", _cancel)
        try:
            self.root.wait_window(win)
        except Exception:
            pass
        return choice["v"]

    # ---------- MSGBOX / WAIT ----------
    def message(self, text, title=""):
        super().message(text, title)
        if self._closed:
            return
        try:
            from tkinter import messagebox as _mb
            _mb.showinfo(str(title or "HxBase"), str(text), parent=self.root)
        except Exception:
            pass

    def wait(self, msg=""):
        super().wait(msg)
        if self._closed:
            return
        try:
            from tkinter import messagebox as _mb
            _mb.showinfo("HxBase", str(msg or "Enter..."), parent=self.root)
        except Exception:
            pass

    # ---------- BROWSE: valodi tablazat ----------
    def browse(self, alias, columns, rows, widths=None):
        super().browse(alias, columns, rows, widths)
        if self._closed:
            return
        import tkinter as tk
        from tkinter import ttk as _ttk
        win = tk.Toplevel(self.root)
        win.title("BROWSE - %s" % alias)
        try:
            win.transient(self.root)
        except Exception:
            pass
        cols = ["c%d" % i for i in range(len(columns))]
        tv = _ttk.Treeview(win, columns=cols, show="headings", height=min(24, max(5, len(rows))))
        for i, c in enumerate(columns):
            wpx = 20 + min((widths[i] if widths and i < len(widths) else 10), 40) * 8
            tv.heading("c%d" % i, text=str(c))
            tv.column("c%d" % i, width=wpx, anchor="w")
        for r in rows[:2000]:
            tv.insert("", "end", values=[("" if v is None else str(v)) for v in r])
        sy = tk.Scrollbar(win, orient="vertical", command=tv.yview)
        sx = tk.Scrollbar(win, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tv.pack(side="top", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        tk.Button(win, text="Bezar", command=win.destroy, font=self.font).pack(pady=4)

    # ---------- ACCEPT/INPUT ----------
    def prompt_user(self, text):
        try:
            from tkinter import simpledialog as _sd
            ans = _sd.askstring("HxBase", str(text or "Add meg:"), parent=self.root)
            return ans if ans is not None else ""
        except Exception:
            return ""

    def close(self):
        # program vege: ablak nyitva marad, amig a felhasznalo be nem zarja
        if self._closed:
            return
        try:
            self.root.mainloop()
        except Exception:
            pass
