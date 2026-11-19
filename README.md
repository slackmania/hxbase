# HxBase — modern xBase (Clipper/dBaseIII ihletés)

Kvázi-grafikus (GUI-grid) konzol + SQLite + p-kód + exe-build. Nincs OOP, csak a régi egyszerű nyelv modern elemekkel.

## Gyors indítás

```bat
cd hxbase
python -m hxbase run examples\hello.prg
python -m hxbase run examples\vevok.prg --headless
```

Parancsok:

| parancs | mit csinál |
|---|---|
| `python -m hxbase run app.prg [--headless]` | `.prg` futtatása GUI-grid ablakban (vagy headless) |
| `python -m hxbase compile app.prg -o app.pcode` | fordítás hordozható p-kódra (JSON) |
| `python -m hxbase runpcode app.pcode [--headless]` | p-kód futtatása (a futtató önmagában) |
| `python -m hxbase build app.prg -o dist\app.exe` | p-kód + runtime beágyazása → önálló `.exe` (PyInstallerrel), fallback: hordozható mappa |

## Nyelv (MVP, lásd SPEC.md)

- `@ sor,oszlop SAY kif [COLOR "W/B"]`, `@ sor,oszlop GET valto`, `READ`, `CLEAR`, `?`, `??`
- `IF/ELSEIF/ELSE/ENDIF`, `DO WHILE/ENDDO`, `FOR/NEXT`, `DO CASE/CASE/OTHERWISE/ENDCASE`, `EXIT/LOOP`
- `FUNCTION/PROCEDURE ... RETURN`, `DO nev()`, `TRY/CATCH/ENDTRY`
- DBF-szemantika SQLite felett: `CREATE tab (nev C(30), kor N(3), szul D, aktiv L)`, `USE`, `SELECT`, `APPEND BLANK`, `REPLACE mezo WITH kif`, `SKIP`, `GO TOP/BOTTOM/n`, `SEEK`, `LOCATE FOR/CONTINUE`, `DELETE/RECALL/PACK/ZAP`, `LIST`, `BROWSE`, `INDEX ON mezo TO tag`, `SQL "..."`
- Modern: `JSONSTRING()`, `JSONPARSE()`, `HTTPGET(url)`, `FILE()`, UTF-8, `.db` fájlok
- GUI-grid: 80x25 Tkinter ablak (sötét konzol), `MENU "a,b,c" TO v TITLE "t"`, `MSGBOX()`

## Exe-modell

1. `compile`: `.prg` → `.pcode` (AST-JSON, 1. verzió).
2. `build`: stub VM + beágyazott p-kód → PyInstaller `--onefile` → `app.exe`. Telepítés nélkül fut, az SQLite statikusan a csomagban van.

## Követelmény

Csak Python 3.10+ (Tkinter + sqlite3 a stdlibben). Exe-hez: `pip install pyinstaller`.
