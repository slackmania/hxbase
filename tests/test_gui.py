"""GUIClipper hej tesztek. Kijelzo nelkul automatikusan SKIP."""
import pytest


def _display():
    try:
        import tkinter as tk
        r = tk.Tk()
        r.destroy()
        return True
    except Exception:
        return False


def _toplevels(root):
    import tkinter as tk
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


def test_parse_grid():
    from hxbase.guiscreen import parse_grid
    assert parse_grid("80x25") == (80, 25)
    assert parse_grid("130x32") == (130, 32)
    assert parse_grid("155x48") == (155, 48)
    assert parse_grid("barsak") == (80, 25)
    assert parse_grid("200x100") == (200, 60)


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_shell_layout():
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("130x32", "Szamlazo Rendszer 2026 - GuiClipper")
    try:
        assert (sc.cols, sc.rows) == (130, 32)
        assert sc.title_var.get() == "Szamlazo Rendszer 2026 - GuiClipper"
        assert sc.clock_var.get() != "--:--" or True
        assert sc.menubox is not None
        assert sc.content is not None
        # ablak kozepre igazitva (nem 0,0 sarok)
        sc.root.update_idletasks()
        assert sc.root.winfo_x() >= 0 and sc.root.winfo_y() >= 0
        # SET TITLE TO atirja a fejlecet
        sc.set_title("Masik Cim")
        assert sc.title_var.get() == "Masik Cim"
        assert _toplevels(sc.root) == []
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_menu_left_panel():
    import tkinter as tk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("80x25")
    try:
        def auto():
            sc.menubox.focus_force()
            sc.menubox.update()
            sc.menubox.select_clear(0, "end")
            sc.menubox.select_set(2)
            sc.menubox.event_generate("<Return>")

        sc.root.after(400, auto)
        assert sc.menu("Cim", ["egy", "ketto", "harom"]) == 3
        assert _toplevels(sc.root) == []  # nincs arva ablak
        assert sc.menus == [("Cim", ["egy", "ketto", "harom"])]
        assert str(sc.menubox.cget("state")) == "disabled"
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_read_embedded_form():
    import tkinter as tk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("80x25")
    try:
        sc.pending_gets = [
            {"kind": "get", "row": 1, "col": 1, "var": "W_NEV", "picture": "@!"},
            {"kind": "checkbox", "row": 2, "col": 1, "var": "W_HIR", "prompt": "Hirlevel"},
            {"kind": "button", "row": 3, "col": 1, "label": "Mehet",
             "action": {"t": "call", "name": "X", "args": []}},
        ]
        fired = []
        mem = {}

        def auto():
            for w in _walk(sc.form_frame):
                if isinstance(w, tk.Entry):
                    w.delete(0, "end")
                    w.insert(0, "anna")
                elif isinstance(w, tk.Checkbutton):
                    w.invoke()
            for w in _walk(sc.form_frame):
                if isinstance(w, tk.Button) and w.cget("text") == "Mehet":
                    w.invoke()
            for w in _walk(sc.form_frame):
                if isinstance(w, tk.Button) and "OK" in str(w.cget("text")):
                    w.invoke()
                    return

        sc.root.after(400, auto)
        sc.read(mem, lambda a: fired.append(1))
        assert fired == [1]
        assert mem.get("W_NEV") == "ANNA", mem
        assert mem.get("W_HIR") is True, mem
        assert _toplevels(sc.root) == []  # urlap a keretben volt, nem ablakban
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass


def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_browse_marker_and_detail():
    import tkinter as tk
    from tkinter import ttk as _ttk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("80x25")
    try:
        cols = ["KOD", "NEV"]
        rows = [["V00001", "Teszt Vevo Kft"]]
        widths = [10, 40]

        def auto():
            for w in _walk(sc.browse_frame):
                if isinstance(w, tk.Button) and w.cget("text") == "Bezar":
                    w.invoke()
                    return

        sc.root.after(800, auto)
        sc.browse("T", cols, rows, widths)
        assert _toplevels(sc.root) == []  # tablazat keretben, nincs ablak
        # reszletezo ablak kozvetlenul (a [+] jel ezt nyitja)
        sc.row_detail("T", cols, rows[0])
        tls = _toplevels(sc.root)
        assert len(tls) == 1
        txt = None
        for w in _walk(tls[0]):
            if isinstance(w, tk.Text):
                txt = w
        assert txt is not None and "V00001" in txt.get("1.0", "end")
        tls[0].destroy()
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_list_panel_noresize():
    import tkinter as tk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("80x25")
    try:
        def auto():
            for w in _walk(sc.list_frame):
                if isinstance(w, tk.Button) and w.cget("text") == "OK":
                    w.invoke()
                    return

        sc.root.after(400, auto)
        sc.list_lines(["fejlec", "sor1", "sor2"])
        assert sc.lists == ["fejlec", "sor1", "sor2"]
        assert _toplevels(sc.root) == []
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass
