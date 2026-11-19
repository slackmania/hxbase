* HxBase demo 2: SQLite DBF-szemantikaval
CLEAR
CREATE vevok (nev C(30), kor N(3), aktiv L)
USE vevok
APPEND BLANK
REPLACE nev WITH "Kiss Anna", kor WITH 34, aktiv WITH .T.
APPEND BLANK
REPLACE nev WITH "Nagy Bela", kor WITH 41, aktiv WITH .F.
GO TOP
@ 2,5 SAY "Vevok listaja:" COLOR "W/B"
LIST
LOCATE FOR kor > 35
IF .NOT. EOF()
  @ 10,5 SAY "35 felett: " + ALLTRIM(nev)
ELSE
  @ 10,5 SAY "Nincs 35 feletti."
ENDIF
BROWSE
