* WIDGETS - CHECKBOX / RADIO / BUTTON + uj fuggvenyek
CLEAR
@ 2,10 SAY "WIDGET DEMO - graphic-env-clipper ihletes" COLOR "W/B"
@ 4,10 SAY "Neved:"
@ 4,18 GET w_nev PICTURE "@!"
@ 5,10 CHECKBOX w_hir PROMPT "Hirlevelet kerek"
@ 6,10 RADIO w_fiz OPTIONS "KP,Bankkartya,Atutalas" TITLE "Fizetes"
@ 8,10 BUTTON "Rendben" ACTION kesz()
@ 8,25 BUTTON "Megse" ACTION megse()
READ
@ 12,10 SAY "Nev: " + ALLTRIM(w_nev)
@ 13,10 SAY "Hirlevel: " + IIF(w_hir, "igen", "nem") + "  Osszeg: " + TRANSFORM(1234567.8, "999,999.99")
@ 14,10 SAY "Fizetes: " + STR(w_fiz)
@ 16,10 SAY "REPLICATE: " + REPLICATE("*", 5)
@ 17,10 SAY "PADL: [" + PADL("12", 5, "0") + "]  SPACE(3) hossza: " + STR(LEN(SPACE(3)))
? VALTYPE(w_nev) + "/" + VALTYPE(w_fiz) + "/" + VALTYPE(w_hir)

FUNCTION kesz()
  ? "OK: " + ALLTRIM(w_nev)
RETURN

FUNCTION megse()
  ? "Megse nyomva"
RETURN
