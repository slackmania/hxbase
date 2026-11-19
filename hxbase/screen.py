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

    def list_out(self, text):
        self.lists.append(text)

    def wait(self, msg=""):
        self.messages.append(("", msg))

    def close(self):
        pass


class GuiScreen(HeadlessScreen):
    """Tkinter ablak: sotet konzol-ablak monospace betuvel + GET-bevitel Entry-vel."""

    def __init__(self, rows=ROW_COUNT, cols=COL_COUNT):
        super().__init__(rows, cols)
        import tkinter as tk
        from tkinter import font as tkfont
        self._tk = tk
        self.root = tk.Tk()
        self.root.title("HxBase — kvázi-grafikus konzol")
        self.root.configure(bg="black")
        self.font = tkfont.Font(family="Consolas", size=11)
        if "Consolas" not in self.font.actual("family"):
            self.font = tkfont.Font(family="Courier New", size=11)
        self.text = tk.Text(
            self.root, width=cols, height=rows, bg="black", fg="white",
            font=self.font, insertbackground="white", wrap="none",
        )
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("def", foreground="white", background="black")
        self._entries = []
        self._closed = False
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._closed = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def _refresh(self):
        self.text.delete("1.0", "end")
        for r in range(self.rows):
            line = "".join(self.buf[r])
            self.text.insert("end", line + ("\n" if r < self.rows - 1 else ""))
        self.root.update_idletasks()

    def clear(self):
        super().clear()
        for e in self._entries:
            try:
                e.destroy()
            except Exception:
                pass
        self._entries = []
        if not self._closed:
            self._refresh()

    def say(self, row, col, text, color=None):
        super().say(row, col, text, color)
        if not self._closed:
            self._refresh()

    def _cell_xy(self, row, col):
        fw = self.font.measure("M")
        fh = self.font.metrics("linespace")
        return col * fw + 4, row * fh + 2

    def read(self, memvars, action_fn=None):
        if self._closed:
            return super().read(memvars, action_fn)
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title("Adatbevitel (READ)")
        win.configure(bg="#111111")
        vars_ = {}   # MEMVAR -> StringVar/IntVar/BooleanVar
        kinds = {}   # MEMVAR -> kind
        pics = {}
        for g in self.pending_gets:
            kind = g.get("kind", "get")
            frame = tk.Frame(win, bg="#111111")
            frame.pack(fill="x", padx=8, pady=2)
            if kind == "get":
                tk.Label(frame, text=f"{g['var']} ({g['row']},{g['col']}):",
                         bg="#111111", fg="white", font=self.font).pack(side="left")
                sv = tk.StringVar(value=str(memvars.get(g["var"].upper(), "")))
                tk.Entry(frame, textvariable=sv, font=self.font, width=30,
                         bg="white", fg="black").pack(side="left", padx=6)
                vars_[g["var"].upper()] = sv
                kinds[g["var"].upper()] = "get"
                pics[g["var"].upper()] = g.get("picture")
                x, y = self._cell_xy(g["row"], g["col"])
                ghost = tk.Entry(self.root, font=self.font, width=20)
                ghost.place(x=x, y=y)
                ghost.insert(0, sv.get())
                self._entries.append(ghost)
            elif kind == "checkbox":
                bv = tk.BooleanVar(value=bool(memvars.get(g["var"].upper(), False)))
                tk.Checkbutton(frame, text=str(g.get("prompt") or g["var"]),
                               variable=bv, bg="#111111", fg="white", selectcolor="#333333",
                               font=self.font).pack(side="left")
                vars_[g["var"].upper()] = bv
                kinds[g["var"].upper()] = "checkbox"
            elif kind == "radio":
                opts = g.get("options") or []
                tk.Label(frame, text=str(g.get("title") or g["var"]) + ":",
                         bg="#111111", fg="white", font=self.font).pack(anchor="w")
                iv = tk.IntVar(value=int(memvars.get(g["var"].upper(), 1) or 1))
                for i, o in enumerate(opts, 1):
                    tk.Radiobutton(frame, text=str(o), value=i, variable=iv,
                                   bg="#111111", fg="white", selectcolor="#333333",
                                   font=self.font).pack(anchor="w", padx=12)
                vars_[g["var"].upper()] = iv
                kinds[g["var"].upper()] = "radio"
            elif kind == "button":
                act = g.get("action")
                def _fire(a=act):
                    try:
                        if action_fn is not None:
                            action_fn(a)
                    except Exception as e:
                        try:
                            memvars["ERROR"] = str(e)
                        except Exception:
                            pass
                tk.Button(frame, text=str(g.get("label")), command=_fire,
                          font=self.font, bg="#225522", fg="white").pack(side="left", padx=6)
        done = {"ok": False}

        def ok(_=None):
            done["ok"] = True
            win.destroy()

        tk.Button(win, text="OK (Enter)", command=ok).pack(pady=6)
        win.bind("<Return>", ok)
        # varakozas modalisan
        try:
            self.root.wait_window(win)
        except Exception:
            pass
        for k, sv in vars_.items():
            try:
                v = sv.get()
                if kinds.get(k) == "get":
                    v = HeadlessScreen._apply_picture(v, pics.get(k))
                memvars[k] = v
            except Exception:
                pass
        # ghostok frissitese + takaritas
        for e in self._entries:
            try:
                e.destroy()
            except Exception:
                pass
        self._entries = []
        self.pending_gets = []
        self._refresh()

    def message(self, text, title=""):
        super().message(text, title)
        if self._closed:
            return
        import tkinter.messagebox as mb
        try:
            mb.showinfo(title or "HxBase", str(text))
        except Exception:
            pass

    def menu(self, title, options):
        super_menu_ret = len(self.menus)  # mar rogzitettuk? nem, Headless koszon...
        # felulirjuk: valodi valaszto ablak
        if self._closed or not options:
            return 1 if options else 0
        import tkinter as tk
        self.choice = {"v": 0}
        win = tk.Toplevel(self.root)
        win.title(title or "Menü")
        tk.Label(win, text=title or "Válassz:", font=self.font).pack(padx=10, pady=6)
        lb = tk.Listbox(win, font=self.font, width=40, height=min(12, len(options)))
        for o in options:
            lb.insert("end", o)
        lb.pack(padx=10, pady=4)
        lb.select_set(0)

        def ok(_=None):
            try:
                sel = lb.curselection()
                self.choice["v"] = (sel[0] + 1) if sel else 0
            except Exception:
                self.choice["v"] = 0
            win.destroy()

        tk.Button(win, text="OK", command=ok).pack(pady=6)
        lb.bind("<Double-Button-1>", ok)
        try:
            self.root.wait_window(win)
        except Exception:
            pass
        return self.choice["v"]

    def browse(self, alias, columns, rows, widths=None):
        super().browse(alias, columns, rows, widths)
        if self._closed:
            return
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title(f"BROWSE — {alias}")
        txt = tk.Text(win, width=min(120, 10 + sum(min((widths[i] if widths and i < len(widths) else 10), 30) + 2 for i in range(len(columns)))),
                      height=min(24, max(5, len(rows) + 4)), font=self.font)
        txt.pack(fill="both", expand=True)
        for line in format_table(columns, rows[:500], widths):
            txt.insert("end", line + "\n")
        tk.Button(win, text="Bezár", command=win.destroy).pack(pady=4)

    def list_out(self, text):
        super().list_out(text)
        if not self._closed:
            # also lecteti a grid aljara? egyszeruen statuszba irjuk
            pass

    def mainloop(self):
        if not self._closed:
            self.root.mainloop()

    def close(self):
        pass
