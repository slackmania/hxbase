"""HxBase CLI: run / compile / runpcode / build."""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys

from .compiler import compile_file, compile_source, save_pcode, load_pcode
from .db import DBManager
from .screen import ConsoleScreen, HeadlessScreen
from .vm import VM


def make_screen(headless, gui=False, grid="80x25"):
    if headless:
        return HeadlessScreen()
    if gui:
        try:
            from .guiscreen import GuiScreen
            return GuiScreen(grid)
        except Exception as e:
            print(f"[hxbase] GUI nem indult ({e}), konzol mod.", file=sys.stderr)
    from .guiscreen import parse_grid
    cols, rows = parse_grid(grid)
    return ConsoleScreen(rows, cols)


def cmd_run(args):
    base_dir = args.dir or (os.path.dirname(os.path.abspath(args.prog)) if args.prog else ".")
    os.makedirs(base_dir, exist_ok=True)
    with open(args.prog, encoding="utf-8") as f:
        src = f.read()
    from .compiler import compile_source
    pcode = compile_source(src)
    screen = make_screen(args.headless, getattr(args, "gui", False), getattr(args, "grid", "80x25"))
    # peldaknal hasznos elore toltott GET-ertekek kornyezeti valtozobol? nem kell
    dbm = DBManager(base_dir)
    vm = VM(screen, dbm, base_dir)
    try:
        vm.run_code(pcode["code"])
    finally:
        try:
            dbm.close_all()
        except Exception:
            pass
    # headless dump, hogy latszodjon a kepernyo tartalma; konzolra eloben rajzolunk
    if type(screen) is HeadlessScreen:
        dump = screen.dump()
        if dump.strip():
            print("---- kepernyo ----")
            print(dump)
        for t, x in screen.messages:
            print(f"[uzenet] {t}: {x}" if t else f"[uzenet] {x}")
        for line in screen.lists:
            print(line)
    else:
        try:
            screen.close()
        except Exception:
            pass


def cmd_compile(args):
    pcode = compile_file(args.prog)
    out = args.o or (os.path.splitext(args.prog)[0] + ".pcode")
    save_pcode(pcode, out)
    print(f"OK: {args.prog} -> {out} ({len(pcode['code'])} utasitas)")


def cmd_runpcode(args):
    pcode = load_pcode(args.pcode)
    base_dir = args.dir or (os.path.dirname(os.path.abspath(args.pcode)) or ".")
    screen = make_screen(args.headless, getattr(args, "gui", False), getattr(args, "grid", "80x25"))
    dbm = DBManager(base_dir)
    vm = VM(screen, dbm, base_dir)
    try:
        vm.run_code(pcode["code"])
    finally:
        try:
            dbm.close_all()
        except Exception:
            pass
    if type(screen) is HeadlessScreen:
        dump = screen.dump()
        if dump.strip():
            print("---- kepernyo ----")
            print(dump)
        for line in screen.lists:
            print(line)
    else:
        try:
            screen.close()
        except Exception:
            pass


def cmd_build(args):
    """app.prg -> app.pcode -> fused standalone.py -> (PyInstaller) app.exe"""
    src_path = args.prog
    out_exe = args.o or os.path.join("dist", os.path.splitext(os.path.basename(src_path))[0] + (".exe" if os.name == "nt" else ""))
    work = os.path.abspath("_hxbuild")
    os.makedirs(work, exist_ok=True)
    pcode = compile_file(src_path)
    pcode_json = json.dumps(pcode, ensure_ascii=False)
    b64 = base64.b64encode(pcode_json.encode("utf-8")).decode()
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    # standalone loader: beagyazott pcode + hxbase runtime import (mellekelt csomagbol)
    stub = f'''import base64, json, os, sys
PCODE_B64 = "{b64}"
def _basedir():
    # hordozhato: HXBASE_DIR > exe melle > aktualis konyvtar
    if os.environ.get("HXBASE_DIR"):
        return os.environ["HXBASE_DIR"]
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()
def _grid():
    args = sys.argv[1:]
    g = "80x25"
    for i, a in enumerate(args):
        if a == "--grid" and i + 1 < len(args):
            g = args[i + 1]
        elif a.startswith("--grid="):
            g = a.split("=", 1)[1]
    return os.environ.get("HXBASE_GRID", g)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() and not getattr(sys, "frozen", False) else None
from hxbase.screen import ConsoleScreen, HeadlessScreen
from hxbase.db import DBManager
from hxbase.vm import VM
from hxbase.guiscreen import parse_grid
def _screen():
    # GUIClipper: GUI az alapertelmezett, headless csak kerese; hiba eseten konzol.
    args = sys.argv[1:]
    headless = "--headless" in args or os.environ.get("HXBASE_HEADLESS") == "1"
    if headless:
        return HeadlessScreen()
    if "--console" in args or os.environ.get("HXBASE_GUI", "1") == "0":
        cols, rows = parse_grid(_grid())
        return ConsoleScreen(rows, cols)
    try:
        from hxbase.guiscreen import GuiScreen
        return GuiScreen(_grid())
    except Exception as e:
        print("[hxbase] GUI nem indult (%s), konzol mod." % e)
        cols, rows = parse_grid(_grid())
        return ConsoleScreen(rows, cols)
def main():
    base = _basedir()
    pcode = json.loads(base64.b64decode(PCODE_B64).decode("utf-8"))
    sc = _screen()
    dbm = DBManager(base)
    vm = VM(sc, dbm, base)
    try:
        vm.run_code(pcode["code"])
    finally:
        try: dbm.close_all()
        except Exception: pass
    if type(sc) is HeadlessScreen:
        d = sc.dump()
        if d.strip():
            print("---- kepernyo ----"); print(d)
        for line in sc.lists: print(line)
    else:
        try: sc.close()
        except Exception: pass
if __name__ == "__main__":
    main()
'''
    # dist konyvtar: hxbase csomag masolasa + stub
    dist_src = os.path.join(work, "app_src")
    if os.path.exists(dist_src):
        shutil.rmtree(dist_src)
    os.makedirs(dist_src)
    shutil.copytree(pkg_dir, os.path.join(dist_src, "hxbase"))
    with open(os.path.join(dist_src, "_boot.py"), "w", encoding="utf-8") as f:
        f.write(stub)
    fused = os.path.join(work, "standalone.py")
    import re as _re
    _m = _re.search(r"^sys\.path\.insert.*$", stub, _re.M)
    fused_stub = stub.replace(_m.group(0), f"sys.path.insert(0, {json.dumps(dist_src)})") if _m else stub
    with open(fused, "w", encoding="utf-8") as f:
        f.write(fused_stub)
    print(f"p-kod beagyazva: {len(pcode['code'])} utasitas")
    print(f"forras-csomag: {dist_src}")
    # PyInstaller kiserlet
    exe_out = os.path.abspath(out_exe)
    os.makedirs(os.path.dirname(exe_out) or ".", exist_ok=True)
    try:
        print("PyInstaller keresese...")
        r = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print("PyInstaller nincs telepítve, probalom telepiteni...")
            ins = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"], timeout=300)
            if ins.returncode != 0:
                raise RuntimeError("pip install pyinstaller sikertelen")
        cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--console", "--clean",
               "--name", os.path.splitext(os.path.basename(exe_out))[0],
               "--paths", dist_src,
               "--hidden-import", "hxbase",
               "--hidden-import", "hxbase.screen",
               "--hidden-import", "hxbase.db",
               "--hidden-import", "hxbase.vm",
               "--hidden-import", "hxbase.parser",
               "--hidden-import", "hxbase.compiler",
               "--hidden-import", "hxbase.lexer",
               "--hidden-import", "hxbase.guiscreen",
               "--hidden-import", "hxbase.pdf",
               "--distpath", os.path.dirname(exe_out) or ".",
               "--workpath", os.path.join(work, "pyi_build"),
               "--specpath", work,
               os.path.join(dist_src, "_boot.py")]
        # sztenderd konyvtar + sqlite3, kulso fuggoseg nincs
        print("EXE keszites: " + " ".join(cmd))
        pr = subprocess.run(cmd, timeout=600)
        if pr.returncode == 0 and os.path.exists(exe_out):
            print(f"KESZ: {exe_out} ({os.path.getsize(exe_out)} bajt) — onmagaban futtathato.")
            return
        print("PyInstaller nem sikerult, fallback: hordozhato mappa + zip.")
    except Exception as e:
        print(f"PyInstaller hiba ({e}), fallback.")
    # fallback: hordozhato mappa + indito
    port = os.path.join(os.path.dirname(exe_out) or ".", "portable_app")
    if os.path.exists(port):
        shutil.rmtree(port)
    shutil.copytree(dist_src, port)
    with open(os.path.join(port, "futtat.bat"), "w", encoding="utf-8") as f:
        f.write('python _boot.py %*\n')
    print(f"Fallback kesz: {port} (+ futtat.bat). Exe-hez: pip install pyinstaller, majd hxbase build.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hxbase", description="HxBase — xBase MVP futtato/fordito")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help=".prg futtatasa")
    r.add_argument("prog")
    r.add_argument("--headless", action="store_true")
    r.add_argument("--gui", action="store_true", help="GUIClipper mod (Tkinter)")
    r.add_argument("--grid", default="80x25", help="racsmeret: 80x25, 130x32, 155x48")
    r.add_argument("--dir", default=None)
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("compile", help=".prg -> .pcode")
    c.add_argument("prog")
    c.add_argument("-o", default=None)
    c.set_defaults(fn=cmd_compile)
    rp = sub.add_parser("runpcode", help=".pcode futtatasa")
    rp.add_argument("pcode")
    rp.add_argument("--headless", action="store_true")
    rp.add_argument("--gui", action="store_true", help="GUIClipper mod (Tkinter)")
    rp.add_argument("--grid", default="80x25", help="racsmeret: 80x25, 130x32, 155x48")
    rp.add_argument("--dir", default=None)
    rp.set_defaults(fn=cmd_runpcode)
    b = sub.add_parser("build", help=".prg -> hordozhato .exe (p-kod beagyazva)")
    b.add_argument("prog")
    b.add_argument("-o", default=None)
    b.set_defaults(fn=cmd_build)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
