# HxBase — modern xBase (Clipper/dBaseIII ihletés)

Tisztán szöveges konzol (80×25-ös rács, ANSI) + SQLite + p-kód + exe-build. Nincs OOP, nincs GUI, csak a régi egyszerű nyelv modern elemekkel.

## Gyors indítás

```bat
cd hxbase
python -m hxbase run examples\hello.prg
python -m hxbase run examples\vevok.prg --headless
```

Parancsok:

| parancs | mit csinál |
|---|---|
| `python -m hxbase run app.prg [--headless]` | `.prg` futtatása szöveges konzolon (vagy headless, kimenet-csövezéshez) |
| `python -m hxbase compile app.prg -o app.pcode` | fordítás hordozható p-kódra (JSON) |
| `python -m hxbase runpcode app.pcode [--headless]` | p-kód futtatása (a futtató önmagában) |
| `python -m hxbase build app.prg -o dist\app.exe` | p-kód + runtime beágyazása → önálló `.exe` (PyInstallerrel), fallback: hordozható mappa |
| `build.bat forras.prg [kimenet.exe]` | ugyanez egy paranccsal, pl. `build.bat examples\teszt50.prg` → `dist\teszt50.exe` |

Az exe hordozható: a `.db` fájlokat az exe mellé (vagy a `HXBASE_DIR` mappába) teszi, nincs szükség telepített Pythonra. Fejlesztéshez `run`, terjesztéshez `build`.

## Számlázó mintaalkalmazás

`examples/szamla/szamla.prg` — komplett rendszer a nyelvben írva:

- automatikus sorszám (`yxas-YYYY/nnnnnn` számla/storno, `SZ-YYYY/nnnnnn` szállító),
- vevők, cikkek, cégadatok, súlyozott átlagáras raktár (bevét: `új átlagár = (régi készlet×régi ár + bevételezett×ár) / új készlet`),
- szállítólevél készítés készletfogyással, számla a szállítóból (dupla számlázás védelemmel), storno negatív tételekkel + készlet-visszatétellel (dupla storno védelemmel),
- magyar kötelező tartalom (eladó/vevő+adószám, kelt/telj/fizhat, fizetési mód, tételenkénti áfa, összesítők), `PDFSTART/PDFSOR/.../PDFMENT`-tel PDF-be nyomtatható,
- minden ablak más, visszafogott témaszínnel (`SET THEME TO KEK|ZOLD|BARNA|BORDO|SZURKE|ALAP`).

```bat
python -m hxbase run examples\szamla\szamla.prg
build.bat examples\szamla\szamla.prg
```

## Nyelv (MVP, lásd SPEC.md)

- `@ sor,oszlop SAY kif [COLOR "W/B"]`, `@ sor,oszlop GET valto`, `READ`, `CLEAR`, `?`, `??`
- `IF/ELSEIF/ELSE/ENDIF`, `DO WHILE/ENDDO`, `FOR/NEXT`, `DO CASE/CASE/OTHERWISE/ENDCASE`, `EXIT/LOOP`
- `FUNCTION/PROCEDURE ... RETURN`, `DO nev()`, `TRY/CATCH/ENDTRY`
- DBF-szemantika SQLite felett: `CREATE tab (nev C(30), kor N(3), szul D, aktiv L)`, `USE`, `SELECT`, `APPEND BLANK`, `REPLACE mezo WITH kif`, `SKIP`, `GO TOP/BOTTOM/n`, `SEEK`, `LOCATE FOR/CONTINUE`, `DELETE/RECALL/PACK/ZAP`, `LIST`, `BROWSE`, `INDEX ON mezo TO tag`, `SQL "..."`
- Modern: `JSONSTRING()`, `JSONPARSE()`, `HTTPGET(url)`, `FILE()`, UTF-8, `.db` fájlok
- Szöveges konzol: 80x25-ös rács ANSI-val (`MENU "a,b,c" TO v TITLE "t"`, `MSGBOX()` keretes ablakként a rácson)

## Exe-modell

1. `compile`: `.prg` → `.pcode` (AST-JSON, 1. verzió).
2. `build`: stub VM + beágyazott p-kód → PyInstaller `--onefile` → `app.exe`. Telepítés nélkül fut, az SQLite statikusan a csomagban van.

## Követelmény

Csak Python 3.10+ (sqlite3 a stdlibben, külső függőség nincs). Exe-hez: `pip install pyinstaller`.
