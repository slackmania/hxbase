# HxBase nyelvi specifikáció (MVP 0.1.0)

## 1. Cél
dBaseIII/Clipper-érzés: procedurális, workarea-alapú, `USE/SKIP/REPLACE`, `@ SAY/GET`, de `.dbf` helyett SQLite, konzol helyett GUI-grid ablak, modern kiegészítőkkel.

## 2. Lexika
- Kis/nagybetű független kulcsszavak. Megjegyzés: `*`, `//`, `&&`, `NOTE`, `REM`.
- Sztring: `"..."` / `'...'`. Logikai: `.T. .F. .Y. .N.`. Dátum-sztring: ISO `YYYY-MM-DD`.
- Folytatósor: sor végi `;`. Több utasítás egy sorban: `;` elválasztó (stringen kívül).
- Operátorok: `+ - * / % ^`, `= == <> != # < > <= >=`, `$` (tartalmaz), `.AND. .OR. .NOT.`.

## 3. Képernyő (szöveges konzol + GUIClipper)
- `CLEAR [SCREEN]`, `SET COLOR TO "W/B"`.
- `@ r,c SAY kif [COLOR c]`, `@ r,c GET var [PICTURE p]` (`"@!"` = nagybetűsít), `READ`.
- Widgetek, DOS-emulációval (nincs valódi GUI-widget, nincs terminál-echo/előzmény): `READ`-kor a program elmenti a háttér celláit a memóriába, keretes dialógust rajzol a rácsra, nyers billentyűkkel kezel (fel/le nyíl soha nem olvas vissza előzményt, kurzor a rácson villog a szerkesztett pozícióban):
  - `@ r,c CHECKBOX var [PROMPT p]` — `[X]/[ ]` jelölő (`Space`/Enter kapcsol),
  - `@ r,c RADIO var OPTIONS "a,b,c" [TITLE t]` — `< választás >` (nyilak/`Space`/sorszám léptet),
  - `@ r,c BUTTON "felirat" ACTION fuggveny()` — `[ felirat ]`, `Enter`re futtat és tovább lép.
  - `TAB`/`Shift+Tab`/fel/le: séta a mezőkön és gombokon (caption kivételével mindenen megáll), bal/jobb: mezőn belül mozgat, `Enter`: tovább/OK, `Ctrl+W`: kész (OK) bárhonnan, `Esc`: elvetés. `GET`-mezőben gépelés, `Backspace`, `Home/End` működik.
  - `MENU` (nyilak+`Enter`/sorszám), `MSGBOX`, `WAIT`, `ACCEPT`/`INPUT`, `BROWSE`-lapozás (`Q` kilép) szintén nyers billentyűs; pipe-olt (nem-tty) stdin esetén soronkénti beolvasás.
- `? kif [, ...]`, `MENU "a,b,c" TO v [TITLE t]`, `BROWSE`, `MSGBOX(kif)`, `WAIT`, `ACCEPT [TO v] [PROMPT p]`, `INPUT`.
- GUIClipper (`--gui`, `hxbase/guiscreen.py`): ugyanez a nyelv, rendes widgetekkel. Rácsok: `80x25`, `130x32`, `155x48` (`--grid`, exe-nél is). `READ` = űrlap (Entry/Checkbutton/Radiobutton/Button + OK/Megse), `MENU` = Listbox, `MSGBOX`/`WAIT` = üzenetablak, `BROWSE` = Treeview táblázat görgetősávokkal, `ACCEPT`/`INPUT` = beviteli dialógus. Kijelző nélkül automatikus konzol-fallback.

## 4. Adatbázis (SQLite)
- Fájl: `<tabla>.db`, benne `<tabla>` tábla + `_recno`, `_deleted` oszlopok.
- `CREATE [TABLE] nev (mezo TIPUS[(h[,t])], ...)` — típusok: `C(n)` TEXT, `N(w,d)` REAL, `D` TEXT ISO-dátum, `L` INTEGER 0/1, `M` TEXT.
- `USE nev [ALIAS a]` / `USE` (zár), `SELECT n|alias`, `CLOSE [ALL]`.
- Navigáció: `GO TOP|BOTTOM|n`, `SKIP [n]`, `SEEK kif`, `LOCATE FOR felt` / `CONTINUE`, `EOF() BOF() RECNO() RECCOUNT() DELETED()`.
- Írás: `APPEND BLANK`, `REPLACE m WITH kif [, ...]`, `mezo = kif` (mezőre ír ha nincs ilyen memvar), `DELETE [FOR f]` / `RECALL` / `PACK` / `ZAP`.
- Összesítés: `SUM kif TO valto [FOR felt]`, `AVERAGE kif TO valto [FOR felt]`, `COUNT TO valto [FOR felt]`.
- Rendezés/másolás: `SORT TO ujtab ON mezo [/D] [FOR felt]`, `COPY TO fajl DELIMITED`, `APPEND FROM fajl DELIMITED`.
- `SET FILTER TO felt`, `SET DELETED ON|OFF`, `INDEX ON mezo TO tag`, `SQL "SELECT..."`, `LIST [FOR f]` (a `LIST` teljes szélességben nyomtat, nem vágja le a 80-as rács).

## 5. Vezérlés + alprogram
`IF [cond] ... [ELSEIF cond] ... [ELSE] ... ENDIF`, `DO WHILE cond ... ENDDO`, `FOR v = a TO b [STEP s] ... NEXT`, `DO CASE [CASE cond] ... [OTHERWISE] ... ENDCASE`, `EXIT LOOP`, `FUNCTION nev([args]) ... RETURN [kif]` (a `PROCEDURE` alias), `DO nev([args])`, `TRY ... CATCH ... ENDTRY` (`ERROR` memvarba ír).

## 6. Beépített függvények
`UPPER LOWER ALLTRIM LTRIM RTRIM LEN SUBSTR LEFT RIGHT AT STR VAL CHR ASC DATE TIME YEAR MONTH DAY DTOC CTOD DTOS DADD IIF EMPTY INT ROUND ABS MIN MAX EOF BOF RECNO RECCOUNT DELETED ALIAS FILE INKEY JSONSTRING JSONPARSE HTTPGET MSGBOX REPLICATE SPACE PADL PADR PADC STUFF RAT TRANSFORM HFMT STRTRAN VALTYPE FCOUNT FIELDNAME DBFNAME`.
- Dátum-matekozás: `DADD(datum, nap)` ISO-dátumra. Magyar pénzformátum: `HFMT(ertek [, tizedes])` → `1 234,50`. Szövegcsere: `STRTRAN(s, keres, csere)`.
- Témaszínek (csak visszafogott párosítások): `SET THEME TO ALAP|KEK|ZOLD|BORDO|SZURKE|EJSZAKA` — dialógusok, menük, üzenetek színét adja; harsány kombináció nem választható.
- PDF-nyomtatás (stdlib-only, beágyazott): `PDFSTART(fajl)`, `PDFCIM(sor)`, `PDFFEJL(sor)`, `PDFSOR(sor)`, `PDFVONAL()`, `PDFOLDAL()`, `PDFMENT()` → fájl a program mappájába. Példa: `examples/szamla/szamla.prg` (komplett számlázó: vevő, súlyozott raktár, szállítólevél, számla, storno, PDF).

## 7. p-kód + exe
- `compile` a parse-olt AST-t JSON-ba menti (`{version, code}`).
- `runpcode` ugyanazt a VM-et hajtja végre mint `run`.
- `build` a p-kód JSON-t base64-ben a stub-VM-be ágyazza, mellé másolja a `hxbase` csomagot, majd PyInstaller `--onefile` csinál belőle `app.exe`-t.

## 8. Nem-célok (MVP-n kívül)
Nincs OOP, nincs öröklődés, nincs relációs `SET RELATION`, nincs report-generator, nincs tranzakció-nyelv (az `SQL "..."`-on át elérhető).
