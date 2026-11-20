"""HxBase GUIClipper hej: fix alkalmazaskeret, semmi arva ablak.

Szerkezet:
  - felso sav: kozepre cim, alatta alahuzas, jobb sarokban ora:perc,
  - bal oldalt: MINDIG lathato menu (fekete betuk, kek kijeloles),
  - tole jobbra: az eppen aktiv KERET (racs / urlap / uzenet / lista /
    tablazat). Minden tartalom keretben van, arva ablak nincs.
  - ha egy tablazat tul szeles, soronkent [+] jel nyithat reszletezo
    ablakot az adott sorrol (ez az egyetlen megengedett kulon ablak).

Racsmeretek: 80x25 (eredeti), 130x32 (kiterjesztett), 155x48 (extrem).
A .prg-k valtoztatas nelkul futnak, koordinatak az eredeti szerint.
"""

from .screen import HeadlessScreen

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
        c = max(40, min(int(m.group(1)), 200))
        r = max(10, min(int(m.group(2)), 60))
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
    """Tkinter alkalmazashej: fejlec + bal menu + jobb oldali aktiv keret."""

    def __init__(self, grid="80x25", title="HxBase GuiClipper"):
        cols, rows = parse_grid(grid)
        super().__init__(rows, cols)
        self.grid_spec = "%dx%d" % (cols, rows)
        import tkinter as tk
        from tkinter import font as tkfont
        self._tk = tk
        self.root = tk.Tk()  # kijelzo nelkul TclError -> hivo fallbackol
        self.root.title("GuiClipper")
        self.root.configure(bg="#d8d8d8")

        # ---- felso sav: cim kozepen, ora jobb sarokban, alatta alahuzas ----
        hdr = tk.Frame(self.root, bg="#e8e8e8")
        hdr.pack(side="top", fill="x")
        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure(1, weight=0)
        hdr.columnconfigure(2, weight=1)
        self.title_var = tk.StringVar(self.root, value=title)
        tk.Label(hdr, textvariable=self.title_var, font=("Arial", 12, "bold"),
                bg="#e8e8e8", fg="black").grid(row=0, column=1, pady=(4, 0))
        self.clock_var = tk.StringVar(self.root, value="--:--")
        tk.Label(hdr, textvariable=self.clock_var, font=("Arial", 10),
                bg="#e8e8e8", fg="black").grid(row=0, column=2, sticky="e", padx=10)
        tk.Frame(self.root, height=2, bg="gray").pack(side="top", fill="x")

        # ---- also resz: bal menu + jobb tartalom ----
        body = tk.Frame(self.root, bg="#d8d8d8")
        body.pack(side="top", fill="both", expand=True)
        left = tk.Frame(body, bg="#d8d8d8")
        left.pack(side="left", fill="y", padx=(4, 2), pady=4)
        self.menu_title_var = tk.StringVar(self.root, value="Menu")
        tk.Label(left, textvariable=self.menu_title_var, font=("Arial", 9, "bold"),
                 bg="#d8d8d8", fg="black").pack()
        self.menubox = tk.Listbox(left, fg="black", selectbackground="blue",
                                  selectforeground="white", exportselection=False,
                                  font=("Courier New", 10), state="disabled")
        self.menubox.pack(fill="both", expand=True)
        self.content = tk.Frame(body, bg="#d8d8d8")
        self.content.pack(side="right", fill="both", expand=True, padx=(2, 4), pady=4)

        # ---- jobb oldali keretek (egyszerre egy latszik) ----
        size = 11
        self.font = tkfont.Font(family="Consolas", size=size)
        if "Consolas" not in self.font.actual("family"):
            self.font = tkfont.Font(family="Courier New", size=size)
        while size > 6:
            wpx = self.font.measure("M") * cols + 30
            hpx = self.font.metrics("linespace") * rows + 30
            try:
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            except Exception:
                break
            if wpx <= sw - 60 and hpx <= sh - 160:
                break
            size -= 1
            self.font.configure(size=size)
        self.grid_text = tk.Text(self.content, width=cols, height=rows, bg="black",
                                 fg="white", font=self.font, insertbackground="white",
                                 wrap="none", state="disabled", borderwidth=2,
                                 relief="groove", highlightthickness=0)
        self.form_frame = tk.Frame(self.content, bg="#f0f0f0", borderwidth=2, relief="groove")
        self.msg_frame = tk.Frame(self.content, bg="#f0f0f0", borderwidth=2, relief="groove")
        self.list_frame = tk.Frame(self.content, bg="#f0f0f0", borderwidth=2, relief="groove")
        self.browse_frame = tk.Frame(self.content, bg="#f0f0f0", borderwidth=2, relief="groove")
        self._tags = set()
        self._stack = []
        self._current = None
        self._closed = False
        self._show("grid")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center()
        self._tick_clock()

    # ---------- hej-geometria ----------
    def _on_close(self):
        self._closed = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def _center(self):
        try:
            self.root.update_idletasks()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry("+%d+%d" % (max(0, (sw - w) // 2), max(0, (sh - h) // 2)))
        except Exception:
            pass

    def _tick_clock(self):
        if self._closed:
            return
        try:
            import time as _t
            self.clock_var.set(_t.strftime("%H:%M"))
            self.root.after(1000, self._tick_clock)
        except Exception:
            pass

    def set_title(self, title):
        super().set_title(title)
        try:
            self.title_var.set(str(title))
        except Exception:
            pass

    def _frames(self):
        return {"grid": self.grid_text, "form": self.form_frame,
                "msg": self.msg_frame, "list": self.list_frame,
                "browse": self.browse_frame}

    def _show(self, name):
        frames = self._frames()
        if self._current is not None:
            try:
                frames[self._current].pack_forget()
            except Exception:
                pass
            self._stack.append(self._current)
        self._current = name
        try:
            frames[name].pack(fill="both", expand=True)
        except Exception:
            pass

    def _back(self):
        frames = self._frames()
        if self._current is not None:
            try:
                frames[self._current].pack_forget()
            except Exception:
                pass
        self._current = self._stack.pop() if self._stack else "grid"
        try:
            frames[self._current].pack(fill="both", expand=True)
        except Exception:
            pass

    def _to_grid(self):
        try:
            for f in self._frames().values():
                f.pack_forget()
        except Exception:
            pass
        self._stack = []
        self._current = "grid"
        try:
            self.grid_text.pack(fill="both", expand=True)
        except Exception:
            pass

    def _clear_frame(self, frame):
        for w in frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

    # ---------- racs ----------
    def _tag(self, fg, bg):
        name = "c_%s_%s" % (fg, bg)
        if name not in self._tags:
            try:
                self.grid_text.tag_config(name, foreground=_tkc(fg, "white"),
                                           background=_tkc(bg, "black"))
            except Exception:
                pass
            self._tags.add(name)
        return name

    def _refresh(self):
        if self._closed:
            return
        try:
            self.grid_text.configure(state="normal")
            self.grid_text.delete("1.0", "end")
            for r in range(self.rows):
                for c in range(self.cols):
                    fg, bg = self.colors[r][c]
                    self.grid_text.insert("end", self.buf[r][c], self._tag(fg, bg))
                if r < self.rows - 1:
                    self.grid_text.insert("end", "\n")
            self.grid_text.configure(state="disabled")
            self.root.update_idletasks()
        except Exception:
            pass

    def clear(self):
        super().clear()
        self._to_grid()
        self._refresh()

    def say(self, row, col, text, color=None):
        super().say(row, col, text, color)
        self._refresh()

    # ---------- READ: beagyazott urlap-keret ----------
    def _dialog_content(self, g, edits):
        kind = g.get("kind", "get")
        if kind == "get":
            return "%s: [%s]" % (g["var"], str(edits.get(g["var"], ""))[:18])
        if kind == "checkbox":
            return "[%s] %s" % ("X" if edits.get(g["var"], False) else " ",
                                g.get("prompt") or g["var"])
        if kind == "radio":
            opts = g.get("options") or []
            try:
                ch = int(edits.get(g["var"], 1) or 1)
            except Exception:
                ch = 1
            cur = opts[ch - 1] if 1 <= ch <= len(opts) else "?"
            return "%s: < %s >" % (g.get("title") or g["var"], cur)
        return "[ %s ]" % g.get("label")

    def _flush_read(self, focus, vars_, memvars):
        for g in focus:
            var = g.get("var")
            if var is None or var.upper() not in vars_:
                continue
            kind2, v, pic = vars_[var.upper()]
            try:
                val = v.get()
                if kind2 == "get":
                    val = HeadlessScreen._apply_picture(val, pic)
                memvars[var.upper()] = val
            except Exception:
                pass

    def _paint_read(self, focus, memvars):
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                self.say(g["row"], g["col"], str(memvars.get(var.upper(), "")))
            elif kind == "checkbox":
                v = bool(memvars.get(var.upper(), False))
                self.say(g["row"], g["col"],
                         ("[X] " if v else "[ ] ") + str(g.get("prompt") or var))
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

    def _read_entries(self, focus, memvars, action_fn, title):
        """Kozos urlap-motor: beagyazott keret + OK/Megse. True = OK."""
        import tkinter as tk
        snap = dict(memvars)
        fr = self.form_frame
        self._clear_frame(fr)
        tk.Label(fr, text=title, font=("Arial", 10, "bold"),
                 bg="#f0f0f0", fg="black").pack(pady=(6, 2))
        vars_ = {}
        bind_targets = []
        first_entry = {"w": None}
        for g in focus:
            kind = g.get("kind", "get")
            var = g.get("var")
            if kind == "get":
                row = tk.Frame(fr, bg="#f0f0f0")
                row.pack(fill="x", padx=10, pady=2)
                tk.Label(row, text="%s:" % var, bg="#f0f0f0", fg="black",
                         font=self.font, width=12, anchor="w").pack(side="left")
                sv = tk.StringVar(self.root, value=str(memvars.get(var.upper(), "")))
                ent = tk.Entry(row, textvariable=sv, font=self.font, width=30)
                ent.pack(side="left", padx=6)
                vars_[var.upper()] = ("get", sv, g.get("picture"))
                bind_targets.append(ent)
                if first_entry["w"] is None:
                    first_entry["w"] = ent
            elif kind == "checkbox":
                bv = tk.BooleanVar(self.root, value=bool(memvars.get(var.upper(), False)))
                cb = tk.Checkbutton(fr, text=str(g.get("prompt") or var), variable=bv,
                                    bg="#f0f0f0", fg="black", selectcolor="white",
                                    font=self.font, anchor="w")
                cb.pack(fill="x", padx=10, pady=2)
                vars_[var.upper()] = ("checkbox", bv, None)
                bind_targets.append(cb)
            elif kind == "radio":
                opts = g.get("options") or []
                lf = tk.LabelFrame(fr, text=str(g.get("title") or var),
                                   bg="#f0f0f0", fg="black", font=self.font)
                lf.pack(fill="x", padx=10, pady=4)
                iv = tk.IntVar(self.root, value=int(memvars.get(var.upper(), 1) or 1))
                for i, o in enumerate(opts, 1):
                    rb = tk.Radiobutton(lf, text=str(o), value=i, variable=iv,
                                        bg="#f0f0f0", fg="black", selectcolor="white",
                                        font=self.font, anchor="w")
                    rb.pack(fill="x", padx=12)
                    bind_targets.append(rb)
                vars_[var.upper()] = ("radio", iv, None)
            elif kind == "button":
                act = g.get("action")

                def _fire(a=act):
                    self._flush_read(focus, vars_, memvars)
                    try:
                        if action_fn is not None:
                            action_fn(a)
                    except Exception as e:
                        memvars["ERROR"] = str(e)
                    self._refresh()

                btn = tk.Button(fr, text=str(g.get("label")), command=_fire, font=self.font)
                btn.pack(padx=10, pady=3)
                bind_targets.append(btn)
        sig = tk.BooleanVar(self.root, value=False)
        res = {"ok": False}

        def _ok(_=None):
            self._flush_read(focus, vars_, memvars)
            res["ok"] = True
            try:
                sig.set(True)
            except Exception:
                pass

        def _cancel(_=None):
            for k in [k for k in memvars.keys() if k not in snap]:
                del memvars[k]
            memvars.update(snap)
            res["ok"] = False
            try:
                sig.set(True)
            except Exception:
                pass

        btns = tk.Frame(fr, bg="#f0f0f0")
        btns.pack(pady=8)
        okb = tk.Button(btns, text="OK (Enter)", command=_ok, font=self.font)
        okb.pack(side="left", padx=6)
        tk.Button(btns, text="Megse (Esc)", command=_cancel, font=self.font).pack(side="left", padx=6)
        binds = []
        for w in bind_targets + [fr]:
            try:
                b1 = w.bind("<Return>", lambda e: _ok(), add="+")
                b2 = w.bind("<Escape>", lambda e: _cancel(), add="+")
                binds.append((w, b1, b2))
            except Exception:
                pass
        self._show("form")
        try:
            if first_entry["w"] is not None:
                first_entry["w"].focus_set()
            elif focus and focus[0].get("kind", "get") == "button":
                pass
        except Exception:
            pass
        try:
            self.root.wait_variable(sig)
        except Exception:
            pass
        for w, b1, b2 in binds:
            try:
                w.unbind("<Return>", b1)
            except Exception:
                pass
            try:
                w.unbind("<Escape>", b2)
            except Exception:
                pass
        return res["ok"]

    def read(self, memvars, action_fn=None):
        entries = self.pending_gets
        self.pending_gets = []
        if not entries:
            return
        if self._closed:
            return super().read(memvars, action_fn)
        focus = [g for g in entries if g.get("kind", "get") in ("get", "checkbox", "radio", "button")]
        if self._read_entries(focus, memvars, action_fn, "Adatbevitel"):
            self._paint_read(focus, memvars)
        self._to_grid()

    # ---------- MENU: bal oldali fix panel ----------
    def menu(self, title, options):
        self.menus.append((title, options))
        if self._closed or not options:
            return 1 if options else 0
        import tkinter as tk
        opts = [str(o) for o in options]
        self.menu_title_var.set(str(title or "Menu"))
        try:
            self.menubox.configure(state="normal")
            self.menubox.delete(0, "end")
            for o in opts:
                self.menubox.insert("end", o)
            self.menubox.select_clear(0, "end")
            self.menubox.select_set(0)
            self.menubox.focus_set()
        except Exception:
            pass
        sig = tk.BooleanVar(self.root, value=False)
        choice = {"v": 0}

        def _on_key(ev):
            ks = ev.keysym
            try:
                cur = self.menubox.curselection()
                idx = cur[0] if cur else 0
            except Exception:
                idx = 0
            if ks == "Up":
                idx = (idx - 1) % len(opts)
                self.menubox.select_clear(0, "end")
                self.menubox.select_set(idx)
                self.menubox.see(idx)
            elif ks == "Down":
                idx = (idx + 1) % len(opts)
                self.menubox.select_clear(0, "end")
                self.menubox.select_set(idx)
                self.menubox.see(idx)
            elif ks == "Return":
                choice["v"] = idx + 1
                try:
                    sig.set(True)
                except Exception:
                    pass
            elif ks == "Escape":
                choice["v"] = 0
                try:
                    sig.set(True)
                except Exception:
                    pass
            return "break"

        def _on_dbl(_=None):
            try:
                sel = self.menubox.curselection()
                choice["v"] = (sel[0] + 1) if sel else 0
            except Exception:
                choice["v"] = 0
            try:
                sig.set(True)
            except Exception:
                pass

        h1 = self.menubox.bind("<Key>", _on_key, add="+")
        h2 = self.menubox.bind("<Double-Button-1>", _on_dbl, add="+")
        try:
            self.root.wait_variable(sig)
        except Exception:
            pass
        try:
            self.menubox.unbind("<Key>", h1)
        except Exception:
            pass
        try:
            self.menubox.unbind("<Double-Button-1>", h2)
        except Exception:
            pass
        try:
            self.menubox.configure(state="disabled")
        except Exception:
            pass
        return choice["v"]

    # ---------- MSGBOX / WAIT: keretbe agyazott uzenet ----------
    def _show_msg(self, text, title, with_ok=True):
        import tkinter as tk
        fr = self.msg_frame
        self._clear_frame(fr)
        tk.Label(fr, text=str(title), font=("Arial", 10, "bold"),
                 bg="#f0f0f0", fg="black").pack(pady=(10, 2))
        lines = str(text).splitlines() or [""]
        body = tk.Label(fr, text="\n".join(lines), font=self.font,
                       bg="#f0f0f0", fg="black", justify="left")
        body.pack(padx=16, pady=6)
        sig = tk.BooleanVar(self.root, value=False)

        def _ok(_=None):
            try:
                sig.set(True)
            except Exception:
                pass

        if with_ok:
            tk.Button(fr, text="OK (Enter)", command=_ok, font=self.font).pack(pady=8)
        self._show("msg")
        binds = []
        for w in (fr, body):
            try:
                binds.append((w, w.bind("<Return>", lambda e: _ok(), add="+"),
                              w.bind("<Escape>", lambda e: _ok(), add="+")))
            except Exception:
                pass
        try:
            self.root.wait_variable(sig)
        except Exception:
            pass
        for w, b1, b2 in binds:
            for tag, bid in (("<Return>", b1), ("<Escape>", b2)):
                try:
                    w.unbind(tag, bid)
                except Exception:
                    pass

    def message(self, text, title=""):
        super().message(text, title)
        if self._closed:
            return
        self._show_msg(text, title or "HxBase")
        self._back()

    def wait(self, msg=""):
        super().wait(msg)
        if self._closed:
            return
        self._show_msg(str(msg or "..."), "Varakozas")
        self._back()

    # ---------- LIST: olvashato keret ----------
    def list_lines(self, lines):
        HeadlessScreen.list_lines(self, lines)
        if self._closed:
            return
        import tkinter as tk
        fr = self.list_frame
        self._clear_frame(fr)
        tk.Label(fr, text="Lista", font=("Arial", 10, "bold"),
                 bg="#f0f0f0", fg="black").pack(pady=(6, 2))
        txt = tk.Text(fr, font=self.font, bg="white", fg="black",
                      wrap="none", height=min(24, max(5, len(lines) + 1)))
        txt.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sy = tk.Scrollbar(fr, orient="vertical", command=txt.yview)
        sy.pack(side="left", fill="y", pady=6)
        txt.configure(yscrollcommand=sy.set)
        for ln in lines[:2000]:
            txt.insert("end", ln + "\n")
        txt.configure(state="disabled")
        sig = tk.BooleanVar(self.root, value=False)

        def _ok(_=None):
            try:
                sig.set(True)
            except Exception:
                pass

        tk.Button(fr, text="OK", command=_ok, font=self.font).pack(side="left", padx=8)
        self._show("list")
        try:
            self.root.wait_variable(sig)
        except Exception:
            pass
        self._back()

    # ---------- BROWSE: tablazat-keret + [+] reszletezo ----------
    def browse(self, alias, columns, rows, widths=None):
        super().browse(alias, columns, rows, widths)
        if self._closed:
            return
        import tkinter as tk
        from tkinter import ttk as _ttk
        fr = self.browse_frame
        self._clear_frame(fr)
        tk.Label(fr, text="BROWSE - %s" % alias, font=("Arial", 10, "bold"),
                 bg="#f0f0f0", fg="black").pack(pady=(6, 2))
        inner = tk.Frame(fr, bg="#f0f0f0")
        inner.pack(fill="both", expand=True, padx=10)
        cols = ["c%d" % i for i in range(len(columns))]
        need = sum(min((widths[i] if widths and i < len(widths) else 10), 40) * 8 + 16
                     for i in range(len(columns)))
        try:
            self.content.update_idletasks()
            visible = self.content.winfo_width() or 800
        except Exception:
            visible = 800
        wide = need > visible
        show = list(cols)
        if wide:
            show = show + ["mark"]
        tv = _ttk.Treeview(inner, columns=show, show="headings",
                           height=min(22, max(5, len(rows))))
        for i, c in enumerate(columns):
            wpx = min((widths[i] if widths and i < len(widths) else 10), 40) * 8 + 16
            tv.heading("c%d" % i, text=str(c))
            tv.column("c%d" % i, width=wpx, anchor="w", stretch=False)
        if wide:
            tv.heading("mark", text="")
            tv.column("mark", width=34, anchor="center", stretch=False)
        for r in rows[:2000]:
            vals = [("" if v is None else str(v)) for v in r]
            if wide:
                vals = vals + ["[+]"]
            tv.insert("", "end", values=vals)
        sy = tk.Scrollbar(inner, orient="vertical", command=tv.yview)
        sx = tk.Scrollbar(inner, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tv.pack(side="top", fill="both", expand=True)
        sx.pack(side="bottom", fill="x")
        sy.pack(side="right", fill="y")

        def _click(ev):
            try:
                col = tv.identify_column(ev.x)
                rid = tv.identify_row(ev.y)
                if not rid or col != "#%d" % (len(show)):
                    return
                vals = tv.item(rid, "values")
                self.row_detail(alias, columns, vals[:len(columns)])
            except Exception:
                pass

        if wide:
            tv.bind("<ButtonRelease-1>", _click)
        sig = tk.BooleanVar(self.root, value=False)

        def _ok(_=None):
            try:
                sig.set(True)
            except Exception:
                pass

        tk.Button(fr, text="Bezar", command=_ok, font=self.font).pack(pady=6)
        self._show("browse")
        try:
            self.root.wait_variable(sig)
        except Exception:
            pass
        self._back()

    def row_detail(self, alias, columns, values):
        """Egy adatsor reszletezo ablaka (a keret [+] jele nyithatja)."""
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title("%s - sor" % alias)
        try:
            win.transient(self.root)
        except Exception:
            pass
        txt = tk.Text(win, font=self.font, bg="white", fg="black",
                      width=60, height=min(20, len(columns) + 4), wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        for c, v in zip(columns, values):
            txt.insert("end", "%s: %s\n" % (c, v))
        txt.configure(state="disabled")
        tk.Button(win, text="Bezar", command=win.destroy, font=self.font).pack(pady=6)
        try:
            self.root.update_idletasks()
            rw, rh = win.winfo_width(), win.winfo_height()
            rx = self.root.winfo_x() + max(0, (self.root.winfo_width() - rw) // 2)
            ry = self.root.winfo_y() + max(0, (self.root.winfo_height() - rh) // 2)
            win.geometry("+%d+%d" % (rx, ry))
        except Exception:
            pass

    # ---------- ACCEPT/INPUT ----------
    def prompt_user(self, text):
        mem = {"_V": ""}
        entries = [{"kind": "get", "row": 0, "col": 0, "var": "_V", "picture": None}]
        if self._closed:
            return ""
        if self._read_entries(entries, mem, None, str(text or "Add meg:")):
            self._to_grid()
            return mem.get("_V", "")
        self._to_grid()
        return ""

    def close(self):
        # program vege: ablak nyitva marad, amig a felhasznalo be nem zarja
        if self._closed:
            return
        try:
            self.root.mainloop()
        except Exception:
            pass
