* TESZT50 - beviteli ablak + 50 sor + lenyilo (BROWSE) ablak
CLEAR
@ 2,10 SAY "TESZT50 - adatbazis generator" COLOR "W/B"
@ 4,10 SAY "Adatbazis neve:"
@ 4,26 GET dbname
@ 5,10 SAY "(uresen hagyva: teszt50)"
READ
IF EMPTY(dbname)
  dbname = "teszt50"
ENDIF
@ 7,10 SAY "Keszul: " + ALLTRIM(dbname) + ".db"
CLOSE ALL
CREATE dbname (kod N(3), nev C(30), kor N(3), aktiv L)
USE dbname
FOR i = 1 TO 50
  APPEND BLANK
  REPLACE kod WITH i, nev WITH "Teszt Nev " + STR(i), kor WITH 20 + i, aktiv WITH IIF(i % 2 = 0, .T., .F.)
NEXT
GO TOP
@ 9,10 SAY "50 sor feltoltve. Sorok: " + STR(RECCOUNT())
LIST
BROWSE
@ 22,10 SAY "Vege. Nyomj ENTER-t..." COLOR "W/B"
WAIT
