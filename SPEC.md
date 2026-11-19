# HxBase nyelvi specifikáció (MVP 0.1.0)

## 1. Cél
dBaseIII/Clipper-érzés: procedurális, workarea-alapú, `USE/SKIP/REPLACE`, `@ SAY/GET`, de `.dbf` helyett SQLite, konzol helyett GUI-grid ablak, modern kiegészítőkkel.

## 2. Lexika
- Kis/nagybetű független kulcsszavak. Megjegyzés: `*`, `//`, `&&`, `NOTE`, `REM`.
- Sztring: `"..."` / `'...'`. Logikai: `.T. .F. .Y. .N.`. Dátum-sztring: ISO `YYYY-MM-DD`.
- Folytatósor: sor végi `;`. Több utasítás egy sorban: `;` elválasztó (stringen kívül).
- Operátorok: `+ - * / % ^`, `= == <> != # < > <= >=`, `$` (tartalmaz), `.AND. .OR. .NOT.`.

## 3. Képernyő
- `CLEAR [SCREEN]`, `SET COLOR TO "W/B"`.
- `@ r,c SAY kif [COLOR c]`, `@ r,c GET var [PICTURE p]` (`"@!"` = nagybetűsít), `READ`.
- Widgetek, DOS-emulációval (nincs valódi GUI-widget): `READ`-kor a program elmenti a háttér celláit a memóriába, keretes dialógust rajzol a rácsra (`Tab` mozgás, `Space`/Enter kapcsol, `Esc` elvet), majd `OK`-ra visszaolvassa az elmentett hátteret:
  - `@ r,c CHECKBOX var [PROMPT p]` — `[X]/[ ]` jelölő,
  - `@ r,c RADIO var OPTIONS "a,b,c" [TITLE t]` — `< választás >` léptető,
  - `@ r,c BUTTON "felirat" ACTION fuggveny()` — `[ felirat ]`, Enterre futtatja a függvényt, az ablak nyitva marad.
- `? kif [, ...]`, `MENU "a,b,c" TO v [TITLE t]`, `BROWSE`, `MSGBOX(kif)`, `WAIT`, `ACCEPT [TO v] [PROMPT p]`, `INPUT`.

## 4. Adatbázis (SQLite)
- Fájl: `<tabla>.db`, benne `<tabla>` tábla + `_recno`, `_deleted` oszlopok.
- `CREATE [TABLE] nev (mezo TIPUS[(h[,t])], ...)` — típusok: `C(n)` TEXT, `N(w,d)` REAL, `D` TEXT ISO-dátum, `L` INTEGER 0/1, `M` TEXT.
- `USE nev [ALIAS a]` / `USE` (zár), `SELECT n|alias`, `CLOSE [ALL]`.
- Navigáció: `GO TOP|BOTTOM|n`, `SKIP [n]`, `SEEK kif`, `LOCATE FOR felt` / `CONTINUE`, `EOF() BOF() RECNO() RECCOUNT() DELETED()`.
- Írás: `APPEND BLANK`, `REPLACE m WITH kif [, ...]`, `mezo = kif` (mezőre ír ha nincs ilyen memvar), `DELETE [FOR f]` / `RECALL` / `PACK` / `ZAP`.
- Összesítés: `SUM kif TO valto [FOR felt]`, `AVERAGE kif TO valto [FOR felt]`, `COUNT TO valto [FOR felt]`.
- Rendezés/másolás: `SORT TO ujtab ON mezo [/D] [FOR felt]`, `COPY TO fajl DELIMITED`, `APPEND FROM fajl DELIMITED`.
- `SET FILTER TO felt`, `SET DELETED ON|OFF`, `INDEX ON mezo TO tag`, `SQL "SELECT..."`, `LIST [FOR f]`.

## 5. Vezérlés + alprogram
`IF [cond] ... [ELSEIF cond] ... [ELSE] ... ENDIF`, `DO WHILE cond ... ENDDO`, `FOR v = a TO b [STEP s] ... NEXT`, `DO CASE [CASE cond] ... [OTHERWISE] ... ENDCASE`, `EXIT LOOP`, `FUNCTION nev([args]) ... RETURN [kif]` (a `PROCEDURE` alias), `DO nev([args])`, `TRY ... CATCH ... ENDTRY` (`ERROR` memvarba ír).

## 6. Beépített függvények
`UPPER LOWER ALLTRIM LTRIM RTRIM LEN SUBSTR LEFT RIGHT AT STR VAL CHR ASC DATE TIME YEAR MONTH DAY DTOC CTOD IIF EMPTY INT ROUND ABS MIN MAX EOF BOF RECNO RECCOUNT DELETED ALIAS FILE INKEY JSONSTRING JSONPARSE HTTPGET MSGBOX REPLICATE SPACE PADL PADR PADC STUFF RAT TRANSFORM DTOS VALTYPE FCOUNT FIELDNAME DBFNAME`.

## 7. p-kód + exe
- `compile` a parse-olt AST-t JSON-ba menti (`{version, code}`).
- `runpcode` ugyanazt a VM-et hajtja végre mint `run`.
- `build` a p-kód JSON-t base64-ben a stub-VM-be ágyazza, mellé másolja a `hxbase` csomagot, majd PyInstaller `--onefile` csinál belőle `app.exe`-t.

## 8. Nem-célok (MVP-n kívül)
Nincs OOP, nincs öröklődés, nincs relációs `SET RELATION`, nincs report-generator, nincs tranzakció-nyelv (az `SQL "..."`-on át elérhető).
