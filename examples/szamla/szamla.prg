* HX-SZAMLA - komplett szamlazo rendszer
* Vevo, cikk, sulyozott raktar, szallitolevel, szamla, storno, PDF nyomtatas.
* Futtatas: python -m hxbase run examples\szamla\szamla.prg

CLEAR
SET THEME TO KEK
DO adatbazis()
DO fomenu()

* ============ FOMENU ============
FUNCTION fomenu()
  DO WHILE .T.
    SET THEME TO KEK
    CLEAR
    @ 2,10 SAY "HX-SZAMLA - szamlazo rendszer" COLOR "W/B"
    @ 3,10 SAY "sulyozott raktar - storno - PDF"
    MENU "Torzsadatok,Raktar,Szallitolevelek,Szamlak,Listak,Vege" TO m_m TITLE "Fomenu"
    DO CASE
    CASE m_m = 1
      DO torzs()
    CASE m_m = 2
      DO raktar()
    CASE m_m = 3
      DO szallito_mod()
    CASE m_m = 4
      DO szamla_mod()
    CASE m_m = 5
      DO listak()
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

* ============ ADATBAZIS ============
FUNCTION adatbazis()
  TRY
    USE ceg
  CATCH
    CREATE ceg (nev C(40), cim C(60), adoszam C(13))
    USE ceg
    APPEND BLANK
    REPLACE nev WITH "Minta Kft", cim WITH "1234 Budapest, Minta u. 1.", adoszam WITH "12345678-1-11"
  ENDTRY
  TRY
    USE vevo
  CATCH
    CREATE vevo (kod C(10), nev C(40), cim C(60), adoszam C(13))
    USE vevo
  ENDTRY
  TRY
    USE cikk
  CATCH
    CREATE cikk (kod C(10), nev C(40), me C(6), keszlet N(10,2), atlagar N(12,2), eladar N(12,2), afa N(2))
    USE cikk
  ENDTRY
  TRY
    USE sorszam
  CATCH
    CREATE sorszam (ev C(4), tip C(1), utolso N(6))
    USE sorszam
  ENDTRY
  TRY
    USE szall
  CATCH
    CREATE szall (szam C(16), datum D, vevo C(10), megj C(40), szamlazva L, osszeg N(12,2))
    USE szall
  ENDTRY
  TRY
    USE szalltet
  CATCH
    CREATE szalltet (szam C(16), sor N(3), cikk C(10), menny N(10,2), ear N(12,2))
    USE szalltet
  ENDTRY
  TRY
    USE szamla
  CATCH
    CREATE szamla (szam C(16), tipus C(8), datum D, telj D, fizhat D, fizmod C(12), vevo C(10), eredeti C(16), netto N(12,2), afa N(12,2), brutto N(12,2), stornozva L)
    USE szamla
  ENDTRY
  TRY
    USE szamlatet
  CATCH
    CREATE szamlatet (szam C(16), sor N(3), cikk C(10), megnev C(40), menny N(10,2), me C(6), ear N(12,2), afa N(3), netto N(12,2), afaert N(12,2), brutto N(12,2))
    USE szamlatet
  ENDTRY
  CLOSE ALL
  ? "Adatbazis kesz."
RETURN

* ============ SEGEDFUNKCIOK ============
FUNCTION num(m_s)
RETURN VAL(STRTRAN(m_s, ",", "."))

FUNCTION ujszam(m_tip)
  CLOSE ALL
  TRY
    USE sorszam
  CATCH
    CREATE sorszam (ev C(4), tip C(1), utolso N(6))
    USE sorszam
  ENDTRY
  m_ev = SUBSTR(DATE(), 1, 4)
  LOCATE FOR EV = m_ev .AND. TIP = m_tip
  IF EOF()
    APPEND BLANK
    REPLACE ev WITH m_ev, tip WITH m_tip, utolso WITH 0
  ENDIF
  m_uj = UTOLSO + 1
  REPLACE utolso WITH m_uj
  IF m_tip = "S"
    m_kesz = "yxas-" + m_ev + "/" + PADL(STR(m_uj), 6, "0")
  ELSE
    m_kesz = "SZ-" + m_ev + "/" + PADL(STR(m_uj), 6, "0")
  ENDIF
  CLOSE ALL
RETURN m_kesz

FUNCTION legfrissebb_szall()
  CLOSE ALL
  USE szall
  m_talalt = ""
  GO BOTTOM
  DO WHILE .NOT. BOF()
    IF .NOT. SZAMLAZVA
      m_talalt = SZAM
      EXIT
    ENDIF
    SKIP -1
  ENDDO
  CLOSE ALL
RETURN m_talalt

FUNCTION legfrissebb_szamla()
  CLOSE ALL
  USE szamla
  m_talalt = ""
  GO BOTTOM
  DO WHILE .NOT. BOF()
    IF TIPUS = "SZAMLA" .AND. .NOT. STORNOZVA
      m_talalt = SZAM
      EXIT
    ENDIF
    SKIP -1
  ENDDO
  CLOSE ALL
RETURN m_talalt

FUNCTION legfrissebb_barmely()
  CLOSE ALL
  USE szamla
  m_talalt = ""
  GO BOTTOM
  IF .NOT. BOF()
    m_talalt = SZAM
  ENDIF
  CLOSE ALL
RETURN m_talalt

* ============ TORZS ============
FUNCTION torzs()
  DO WHILE .T.
    SET THEME TO ZOLD
    CLEAR
    @ 2,10 SAY "Torzsadatok"
    MENU "Vevok,Cikkek,Cegadatok,Vissza" TO m_m TITLE "Torzs"
    DO CASE
    CASE m_m = 1
      DO vevo_mod()
    CASE m_m = 2
      DO cikk_mod()
    CASE m_m = 3
      DO ceg_mod()
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION vevo_mod()
  DO WHILE .T.
    SET THEME TO ZOLD
    CLEAR
    @ 2,10 SAY "Vevok"
    MENU "Felvitel,Lista,Vissza" TO m_m TITLE "Vevo"
    DO CASE
    CASE m_m = 1
      DO vevo_fel()
    CASE m_m = 2
      CLOSE ALL
      USE vevo
      LIST
      WAIT
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION vevo_fel()
  SET THEME TO ZOLD
  CLOSE ALL
  USE vevo
  CLEAR
  @ 2,10 SAY "Vevo felvitele"
  m_kod = ""
  m_nev = ""
  m_cim = ""
  m_ado = ""
  @ 4,10 SAY "Kod:"
  @ 4,16 GET m_kod PICTURE "@!"
  @ 5,10 SAY "Nev:"
  @ 5,16 GET m_nev
  @ 6,10 SAY "Cim:"
  @ 6,16 GET m_cim
  @ 7,10 SAY "Adoszam:"
  @ 7,20 GET m_ado
  READ
  IF EMPTY(m_kod)
    MSGBOX("Ures kod - nincs rogzitve")
    RETURN
  ENDIF
  LOCATE FOR KOD = m_kod
  IF .NOT. EOF()
    m_uzen = "Mar letezik: " + m_kod
    MSGBOX(m_uzen)
    RETURN
  ENDIF
  APPEND BLANK
  REPLACE kod WITH m_kod, nev WITH m_nev, cim WITH m_cim, adoszam WITH m_ado
  m_uzen = "Rogzitve: " + m_kod
  MSGBOX(m_uzen)
RETURN

FUNCTION cikk_mod()
  DO WHILE .T.
    SET THEME TO ZOLD
    CLEAR
    @ 2,10 SAY "Cikkek"
    MENU "Felvitel,Lista,Vissza" TO m_m TITLE "Cikk"
    DO CASE
    CASE m_m = 1
      DO cikk_fel()
    CASE m_m = 2
      CLOSE ALL
      USE cikk
      LIST
      WAIT
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION cikk_fel()
  SET THEME TO ZOLD
  CLOSE ALL
  USE cikk
  CLEAR
  @ 2,10 SAY "Cikk felvitele"
  m_kod = ""
  m_nev = ""
  m_me = ""
  m_elad = ""
  m_afa = ""
  @ 4,10 SAY "Kod:"
  @ 4,16 GET m_kod PICTURE "@!"
  @ 5,10 SAY "Nev:"
  @ 5,16 GET m_nev
  @ 6,10 SAY "Me:"
  @ 6,16 GET m_me
  @ 7,10 SAY "Eladasi ar:"
  @ 7,22 GET m_elad
  @ 8,10 SAY "AFA %:"
  @ 8,22 GET m_afa
  READ
  IF EMPTY(m_kod)
    MSGBOX("Ures kod - nincs rogzitve")
    RETURN
  ENDIF
  LOCATE FOR KOD = m_kod
  IF .NOT. EOF()
    m_uzen = "Mar letezik: " + m_kod
    MSGBOX(m_uzen)
    RETURN
  ENDIF
  IF EMPTY(m_me)
    m_me = "db"
  ENDIF
  IF EMPTY(m_afa)
    m_afa = "27"
  ENDIF
  APPEND BLANK
  REPLACE kod WITH m_kod, nev WITH m_nev, me WITH m_me, keszlet WITH 0, atlagar WITH 0, eladar WITH NUM(m_elad), afa WITH NUM(m_afa)
  m_uzen = "Rogzitve: " + m_kod
  MSGBOX(m_uzen)
RETURN

FUNCTION ceg_mod()
  SET THEME TO ZOLD
  CLOSE ALL
  USE ceg
  GO TOP
  IF BOF()
    APPEND BLANK
  ENDIF
  m_nev = NEV
  m_cim = CIM
  m_ado = ADOSZAM
  CLEAR
  @ 2,10 SAY "Cegadatok (elado)"
  @ 4,10 SAY "Nev:"
  @ 4,16 GET m_nev
  @ 5,10 SAY "Cim:"
  @ 5,16 GET m_cim
  @ 6,10 SAY "Adoszam:"
  @ 6,20 GET m_ado
  READ
  REPLACE nev WITH m_nev, cim WITH m_cim, adoszam WITH m_ado
  CLOSE ALL
  MSGBOX("Cegadatok mentve")
RETURN

* ============ RAKTAR ============
FUNCTION raktar()
  DO WHILE .T.
    SET THEME TO BARNA
    CLEAR
    @ 2,10 SAY "Raktar (sulyozott atlagar)"
    MENU "Bevetelezes,Keszlet lista,Vissza" TO m_m TITLE "Raktar"
    DO CASE
    CASE m_m = 1
      DO bevet()
    CASE m_m = 2
      CLOSE ALL
      USE cikk
      LIST
      WAIT
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION bevet()
  SET THEME TO BARNA
  CLOSE ALL
  USE cikk
  CLEAR
  @ 2,10 SAY "Bevetelezes"
  m_kod = ""
  m_menny = ""
  m_ar = ""
  @ 4,10 SAY "Cikk kod:"
  @ 4,21 GET m_kod PICTURE "@!"
  @ 5,10 SAY "Mennyiseg:"
  @ 5,21 GET m_menny
  @ 6,10 SAY "Besar ar:"
  @ 6,21 GET m_ar
  READ
  IF EMPTY(m_kod)
    RETURN
  ENDIF
  m_db = NUM(m_menny)
  m_bar = NUM(m_ar)
  IF m_db <= 0
    MSGBOX("Hibas mennyiseg")
    RETURN
  ENDIF
  LOCATE FOR KOD = m_kod
  IF EOF()
    MSGBOX("Nincs ilyen cikk")
    RETURN
  ENDIF
  m_regik = KESZLET
  m_regia = ATLAGAR
  m_ujk = m_regik + m_db
  m_uja = (m_regik * m_regia + m_db * m_bar) / m_ujk
  REPLACE keszlet WITH m_ujk, atlagar WITH m_uja
  m_uzen = "Keszlet: " + HFMT(m_ujk) + "  Atlagar: " + HFMT(m_uja)
  MSGBOX(m_uzen)
RETURN

* ============ SZALLITOLEVEL ============
FUNCTION szallito_mod()
  DO WHILE .T.
    SET THEME TO BORDO
    CLEAR
    @ 2,10 SAY "Szallitolevelek"
    MENU "Uj szallito,Lista,Nyomtatas PDF,Szamlazas,Vissza" TO m_m TITLE "Szallito"
    DO CASE
    CASE m_m = 1
      DO szall_uj()
    CASE m_m = 2
      CLOSE ALL
      USE szall
      LIST
      WAIT
    CASE m_m = 3
      DO szall_pdf()
    CASE m_m = 4
      DO szamla_keszit()
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION szall_uj()
  SET THEME TO BORDO
  CLOSE ALL
  USE szall
  USE szalltet
  USE vevo
  USE cikk
  CLEAR
  @ 2,10 SAY "Uj szallitolevel"
  m_vevo = ""
  m_megj = ""
  @ 4,10 SAY "Vevo kod:"
  @ 4,21 GET m_vevo PICTURE "@!"
  @ 5,10 SAY "Megjegyzes:"
  @ 5,22 GET m_megj
  READ
  IF EMPTY(m_vevo)
    RETURN
  ENDIF
  SELECT vevo
  LOCATE FOR KOD = m_vevo
  IF EOF()
    MSGBOX("Nincs ilyen vevo")
    RETURN
  ENDIF
  m_szam = ujszam("Z")
  CLOSE ALL
  USE szall
  USE szalltet
  USE cikk
  SELECT szall
  APPEND BLANK
  REPLACE szam WITH m_szam, datum WITH DATE(), vevo WITH m_vevo, megj WITH m_megj, szamlazva WITH .F., osszeg WITH 0
  m_sor = 0
  DO WHILE .T.
    CLEAR
    @ 2,10 SAY "Szallito: " + m_szam
    m_cikk = ""
    m_menny = ""
    @ 4,10 SAY "Cikk kod (ures = vege):"
    @ 4,31 GET m_cikk PICTURE "@!"
    @ 5,10 SAY "Mennyiseg:"
    @ 5,21 GET m_menny
    READ
    IF EMPTY(m_cikk)
      EXIT
    ENDIF
    m_db = NUM(m_menny)
    IF m_db <= 0
      MSGBOX("Hibas mennyiseg")
      LOOP
    ENDIF
    SELECT cikk
    LOCATE FOR KOD = m_cikk
    IF EOF()
      MSGBOX("Nincs ilyen cikk")
      LOOP
    ENDIF
    IF KESZLET < m_db
      m_uzen = "Nincs keszlet: " + HFMT(KESZLET)
      MSGBOX(m_uzen)
      LOOP
    ENDIF
    m_ear = ELADAR
    m_sor = m_sor + 1
    SELECT szalltet
    APPEND BLANK
    REPLACE szam WITH m_szam, sor WITH m_sor, cikk WITH m_cikk, menny WITH m_db, ear WITH m_ear
    SELECT cikk
    REPLACE keszlet WITH KESZLET - m_db
    SELECT szalltet
  ENDDO
  SUM menny * ear TO m_ossz FOR szam = m_szam
  SELECT szall
  LOCATE FOR SZAM = m_szam
  REPLACE osszeg WITH m_ossz
  m_uzen = "Szallito kesz: " + m_szam + "  Ertek: " + HFMT(m_ossz)
  MSGBOX(m_uzen)
RETURN

* ============ SZAMLA ============
FUNCTION szamla_mod()
  DO WHILE .T.
    SET THEME TO SZURKE
    CLEAR
    @ 2,10 SAY "Szamlak"
    MENU "Uj szamla szallitobol,Lista,Nyomtatas PDF,Storno,Vissza" TO m_m TITLE "Szamla"
    DO CASE
    CASE m_m = 1
      DO szamla_keszit()
    CASE m_m = 2
      CLOSE ALL
      USE szamla
      LIST
      WAIT
    CASE m_m = 3
      DO szamla_pdf()
    CASE m_m = 4
      DO szamla_storno()
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN

FUNCTION szamla_keszit()
  SET THEME TO SZURKE
  CLOSE ALL
  USE szall
  USE szalltet
  USE szamla
  USE szamlatet
  USE cikk
  USE vevo
  CLEAR
  @ 2,10 SAY "Szamla keszitese szallitobol"
  m_szall = ""
  m_fizmod = ""
  @ 4,10 SAY "Szallito szama (ures = legfrissebb):"
  @ 4,41 GET m_szall PICTURE "@!"
  @ 5,10 SAY "Fizetes modja:"
  @ 5,25 GET m_fizmod
  READ
  IF EMPTY(m_fizmod)
    m_fizmod = "Atutalas"
  ENDIF
  IF EMPTY(m_szall)
    m_szall = legfrissebb_szall()
  ENDIF
  IF EMPTY(m_szall)
    MSGBOX("Nincs szamlazhato szallito")
    RETURN
  ENDIF
  CLOSE ALL
  USE szall
  USE szalltet
  USE szamla
  USE szamlatet
  USE cikk
  USE vevo
  SELECT szall
  LOCATE FOR SZAM = m_szall
  IF EOF()
    MSGBOX("Nincs ilyen szallito")
    RETURN
  ENDIF
  IF SZAMLAZVA
    MSGBOX("Mar szamlazva van")
    RETURN
  ENDIF
  m_vevo = VEVO
  m_kelt = DATE()
  m_telj = DATE()
  m_fizhat = DADD(DATE(), 8)
  m_szam = ujszam("S")
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE szalltet
  USE szall
  USE cikk
  SELECT szamla
  APPEND BLANK
  REPLACE szam WITH m_szam, tipus WITH "SZAMLA", datum WITH m_kelt, telj WITH m_telj, fizhat WITH m_fizhat, fizmod WITH m_fizmod, vevo WITH m_vevo, eredeti WITH "", netto WITH 0, afa WITH 0, brutto WITH 0, stornozva WITH .F.
  m_sor = 0
  SELECT szalltet
  GO TOP
  DO WHILE .NOT. EOF()
    IF SZAM = m_szall
      m_cikk = CIKK
      m_db = MENNY
      m_ear = EAR
      SELECT cikk
      LOCATE FOR KOD = m_cikk
      m_cnev = "?"
      m_cme = "db"
      m_cafa = 27
      IF .NOT. EOF()
        m_cnev = NEV
        m_cme = ME
        m_cafa = AFA
      ENDIF
      m_netto = m_db * m_ear
      m_afaert = m_netto * m_cafa / 100
      m_brutto = m_netto + m_afaert
      m_sor = m_sor + 1
      SELECT szamlatet
      APPEND BLANK
      REPLACE szam WITH m_szam, sor WITH m_sor, cikk WITH m_cikk, megnev WITH m_cnev, menny WITH m_db, me WITH m_cme, ear WITH m_ear, afa WITH m_cafa, netto WITH m_netto, afaert WITH m_afaert, brutto WITH m_brutto
      SELECT szalltet
    ENDIF
    SKIP
  ENDDO
  SELECT szamlatet
  SUM netto TO m_n FOR szam = m_szam
  SUM afaert TO m_a FOR szam = m_szam
  SUM brutto TO m_b FOR szam = m_szam
  SELECT szamla
  LOCATE FOR SZAM = m_szam
  REPLACE netto WITH m_n, afa WITH m_a, brutto WITH m_b
  SELECT szall
  LOCATE FOR SZAM = m_szall
  REPLACE szamlazva WITH .T.
  m_uzen = "Szamla kesz: " + m_szam + "  Brutto: " + HFMT(m_b)
  MSGBOX(m_uzen)
RETURN

FUNCTION szamla_storno()
  SET THEME TO BORDO
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE cikk
  CLEAR
  @ 2,10 SAY "Szamla stornozasa"
  m_eredeti = ""
  @ 4,10 SAY "Eredeti szamla (ures = legfrissebb):"
  @ 4,42 GET m_eredeti PICTURE "@!"
  READ
  IF EMPTY(m_eredeti)
    m_eredeti = legfrissebb_szamla()
  ENDIF
  IF EMPTY(m_eredeti)
    MSGBOX("Nincs stornozhato szamla")
    RETURN
  ENDIF
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE cikk
  SELECT szamla
  LOCATE FOR SZAM = m_eredeti
  IF EOF()
    MSGBOX("Nincs ilyen szamla")
    RETURN
  ENDIF
  IF TIPUS = "STORNO"
    MSGBOX("Ez mar storno szamla")
    RETURN
  ENDIF
  IF STORNOZVA
    MSGBOX("Mar stornozva van")
    RETURN
  ENDIF
  m_vevo = VEVO
  m_fizmod = FIZMOD
  m_n = 0 - NETTO
  m_a = 0 - AFA
  m_b = 0 - BRUTTO
  m_szam = ujszam("S")
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE cikk
  SELECT szamla
  APPEND BLANK
  REPLACE szam WITH m_szam, tipus WITH "STORNO", datum WITH DATE(), telj WITH DATE(), fizhat WITH DATE(), fizmod WITH m_fizmod, vevo WITH m_vevo, eredeti WITH m_eredeti, netto WITH m_n, afa WITH m_a, brutto WITH m_b, stornozva WITH .F.
  m_sor = 0
  SELECT szamlatet
  GO TOP
  DO WHILE .NOT. EOF()
    IF SZAM = m_eredeti
      m_sor = m_sor + 1
      m_cikk = CIKK
      m_db = 0 - MENNY
      SELECT szamlatet
      APPEND BLANK
      REPLACE szam WITH m_szam, sor WITH m_sor, cikk WITH m_cikk, megnev WITH MEGNEV, menny WITH m_db, me WITH ME, ear WITH EAR, afa WITH AFA, netto WITH 0 - NETTO, afaert WITH 0 - AFAERT, brutto WITH 0 - BRUTTO
      SELECT cikk
      LOCATE FOR KOD = m_cikk
      IF .NOT. EOF()
        REPLACE keszlet WITH KESZLET - m_db
      ENDIF
      SELECT szamlatet
    ENDIF
    SKIP
  ENDDO
  SELECT szamla
  LOCATE FOR SZAM = m_eredeti
  REPLACE stornozva WITH .T.
  m_uzen = "Storno kesz: " + m_szam
  MSGBOX(m_uzen)
RETURN

* ============ PDF NYOMTATAS ============
FUNCTION szamla_pdf()
  SET THEME TO SZURKE
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE vevo
  USE ceg
  CLEAR
  @ 2,10 SAY "Szamla nyomtatasa (PDF)"
  m_szam = ""
  @ 4,10 SAY "Szamla szama (ures = legfrissebb):"
  @ 4,41 GET m_szam PICTURE "@!"
  READ
  IF EMPTY(m_szam)
    m_szam = legfrissebb_barmely()
  ENDIF
  IF EMPTY(m_szam)
    MSGBOX("Nincs szamla")
    RETURN
  ENDIF
  CLOSE ALL
  USE szamla
  USE szamlatet
  USE vevo
  USE ceg
  SELECT szamla
  LOCATE FOR SZAM = m_szam
  IF EOF()
    MSGBOX("Nincs ilyen szamla")
    RETURN
  ENDIF
  m_tipus = TIPUS
  m_datum = DATUM
  m_telj = TELJ
  m_fizhat = FIZHAT
  m_fizmod = FIZMOD
  m_vevo = VEVO
  m_eredeti = EREDETI
  m_n = NETTO
  m_a = AFA
  m_b = BRUTTO
  SELECT vevo
  LOCATE FOR KOD = m_vevo
  m_vnev = "?"
  m_vcim = "?"
  m_vado = "?"
  IF .NOT. EOF()
    m_vnev = NEV
    m_vcim = CIM
    m_vado = ADOSZAM
  ENDIF
  SELECT ceg
  GO TOP
  m_cnev = NEV
  m_ccim = CIM
  m_cado = ADOSZAM
  m_fajl = STRTRAN(m_szam, "/", "-") + ".pdf"
  PDFSTART(m_fajl)
  IF m_tipus = "STORNO"
    PDFCIM("STORNO SZAMLA")
  ELSE
    PDFCIM("SZAMLA")
  ENDIF
  PDFSOR("Sorszam: " + m_szam)
  PDFSOR("Kelt: " + m_datum + "  Teljesites: " + m_telj + "  Fiz. hatarido: " + m_fizhat)
  PDFSOR("Fizetes modja: " + m_fizmod)
  PDFFEJL("Elado:")
  PDFSOR(m_cnev)
  PDFSOR(m_ccim)
  PDFSOR("Adoszam: " + m_cado)
  PDFFEJL("Vevo:")
  PDFSOR(m_vnev)
  PDFSOR(m_vcim)
  PDFSOR("Adoszam: " + m_vado)
  PDFFEJL("Tetelek:")
  SELECT szamlatet
  GO TOP
  DO WHILE .NOT. EOF()
    IF SZAM = m_szam
      PDFSOR(STR(SOR) + ". " + ALLTRIM(MEGNEV) + " (" + ALLTRIM(CIKK) + ")")
      PDFSOR("   " + HFMT(MENNY) + " " + ALLTRIM(ME) + " x " + HFMT(EAR) + " = " + HFMT(NETTO) + " + " + STR(AFA) + "% afa " + HFMT(AFAERT) + " = " + HFMT(BRUTTO))
    ENDIF
    SKIP
  ENDDO
  PDFVONAL()
  PDFSOR("Netto osszesen: " + HFMT(m_n))
  PDFSOR("Afa osszesen: " + HFMT(m_a))
  PDFFEJL("FIZETENDO (brutto): " + HFMT(m_b))
  IF m_tipus = "STORNO"
    PDFSOR("Storno - eredeti szamla: " + m_eredeti)
  ENDIF
  PDFSOR("Ervenyes alairas nelkul.")
  PDFMENT()
  m_uzen = "PDF kesz: " + m_fajl
  MSGBOX(m_uzen)
RETURN

FUNCTION szall_pdf()
  SET THEME TO BORDO
  CLOSE ALL
  USE szall
  USE szalltet
  USE vevo
  CLEAR
  @ 2,10 SAY "Szallitolevel nyomtatasa (PDF)"
  m_szam = ""
  @ 4,10 SAY "Szallito szama (ures = legfrissebb):"
  @ 4,41 GET m_szam PICTURE "@!"
  READ
  IF EMPTY(m_szam)
    m_szam = legfrissebb_szall()
  ENDIF
  IF EMPTY(m_szam)
    MSGBOX("Nincs szallitolevel")
    RETURN
  ENDIF
  CLOSE ALL
  USE szall
  USE szalltet
  USE vevo
  USE ceg
  SELECT szall
  LOCATE FOR SZAM = m_szam
  IF EOF()
    MSGBOX("Nincs ilyen szallito")
    RETURN
  ENDIF
  m_datum = DATUM
  m_vevo = VEVO
  m_megj = MEGJ
  SELECT vevo
  LOCATE FOR KOD = m_vevo
  m_vnev = "?"
  m_vcim = "?"
  IF .NOT. EOF()
    m_vnev = NEV
    m_vcim = CIM
  ENDIF
  SELECT ceg
  GO TOP
  m_cnev = NEV
  m_ccim = CIM
  m_fajl = STRTRAN(m_szam, "/", "-") + ".pdf"
  PDFSTART(m_fajl)
  PDFCIM("SZALLITOLEVEL")
  PDFSOR("Sorszam: " + m_szam + "  Datum: " + m_datum)
  PDFFEJL("Szallito:")
  PDFSOR(m_cnev)
  PDFSOR(m_ccim)
  PDFFEJL("Vevo:")
  PDFSOR(m_vnev)
  PDFSOR(m_vcim)
  IF .NOT. EMPTY(m_megj)
    PDFSOR("Megjegyzes: " + m_megj)
  ENDIF
  PDFFEJL("Tetelek:")
  SELECT szalltet
  GO TOP
  DO WHILE .NOT. EOF()
    IF SZAM = m_szam
      PDFSOR(STR(SOR) + ". " + ALLTRIM(CIKK) + " - " + HFMT(MENNY) + " db")
    ENDIF
    SKIP
  ENDDO
  PDFVONAL()
  IF .NOT. EMPTY(m_megj)
    PDFSOR("Megjegyzes: " + m_megj)
  ENDIF
  PDFSOR("Aru atvetve. Alairas: ....................")
  PDFMENT()
  m_uzen = "PDF kesz: " + m_fajl
  MSGBOX(m_uzen)
RETURN

* ============ LISTAK ============
FUNCTION listak()
  DO WHILE .T.
    SET THEME TO ALAP
    CLEAR
    @ 2,10 SAY "Listak"
    MENU "Vevok,Cikkek,Szamlak,Szallitok,Vege" TO m_m TITLE "Listak"
    DO CASE
    CASE m_m = 1
      CLOSE ALL
      USE vevo
      LIST
      WAIT
    CASE m_m = 2
      CLOSE ALL
      USE cikk
      LIST
      WAIT
    CASE m_m = 3
      CLOSE ALL
      USE szamla
      LIST
      WAIT
    CASE m_m = 4
      CLOSE ALL
      USE szall
      LIST
      WAIT
    OTHERWISE
      EXIT
    ENDCASE
  ENDDO
RETURN
