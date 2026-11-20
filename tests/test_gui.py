"""GUIClipper tesztek. Kijelzo nelkul automatikusan SKIP."""
import pytest


def _display():
    try:
        import tkinter as tk
        r = tk.Tk()
        r.destroy()
        return True
    except Exception:
        return False


def test_parse_grid():
    from hxbase.guiscreen import parse_grid
    assert parse_grid("80x25") == (80, 25)
    assert parse_grid("130x32") == (130, 32)
    assert parse_grid("155x48") == (155, 48)
    assert parse_grid("barsak") == (80, 25)
    assert parse_grid("200x100") == (200, 60)


@pytest.mark.skipif(not _display(), reason="nincs kijelzo")
def test_gui_read_form():
    import tkinter as tk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("80x25")
    try:
        sc.pending_gets = [
            {"kind": "get", "row": 1, "col": 1, "var": "W_NEV", "picture": "@!"},
            {"kind": "checkbox", "row": 2, "col": 1, "var": "W_HIR", "prompt": "Hirlevel"},
            {"kind": "radio", "row": 3, "col": 1, "var": "W_FIZ",
             "options": ["a", "b", "c"], "title": "Fiz"},
            {"kind": "button", "row": 4, "col": 1, "label": "Mehet",
             "action": {"t": "call", "name": "X", "args": []}},
        ]
        fired = []
        mem = {}

        def auto():
            for tl in sc.root.winfo_children():
                if not isinstance(tl, tk.Toplevel):
                    continue
                # Entry kitoltese
                for w in _walk(tl):
                    if isinstance(w, tk.Entry):
                        w.delete(0, "end")
                        w.insert(0, "anna")
                    elif isinstance(w, tk.Checkbutton):
                        w.invoke()
                    elif isinstance(w, tk.Radiobutton) and str(w.cget("value")) == "2":
                        w.invoke()
                # action gomb, majd OK
                for w in _walk(tl):
                    if isinstance(w, tk.Button) and w.cget("text") == "Mehet":
                        w.invoke()
                for w in _walk(tl):
                    if isinstance(w, tk.Button) and "OK" in str(w.cget("text")):
                        w.invoke()
                        return

        sc.root.after(400, auto)
        sc.read(mem, lambda a: fired.append(1))
        assert fired == [1]
        assert mem.get("W_NEV") == "ANNA", mem  # PICTURE @! nagybetusit
        assert mem.get("W_HIR") is True, mem
        assert mem.get("W_FIZ") == 2, mem
        assert "ANNA" in sc.dump()
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
def test_gui_menu_and_browse():
    import tkinter as tk
    from hxbase.guiscreen import GuiScreen
    sc = GuiScreen("130x32")
    try:
        assert (sc.cols, sc.rows) == (130, 32)

        def auto():
            for tl in sc.root.winfo_children():
                if not isinstance(tl, tk.Toplevel):
                    continue
                for w in _walk(tl):
                    if isinstance(w, tk.Listbox):
                        w.select_clear(0, "end")
                        w.select_set(2)
                    if isinstance(w, tk.Button) and w.cget("text") == "OK":
                        w.invoke()
                        return

        sc.root.after(400, auto)
        assert sc.menu("Cim", ["egy", "ketto", "harom"]) == 3
        sc.browse("T", ["A", "B"], [["x", 1], ["y", 2]])
        for tl in list(sc.root.winfo_children()):
            try:
                tl.destroy()
            except Exception:
                pass
        assert sc.menus == [("Cim", ["egy", "ketto", "harom"])]
    finally:
        try:
            sc.root.destroy()
        except Exception:
            pass
