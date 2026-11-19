* HxBase demo 3: menu + fuggveny + modern JSON
CLEAR
MENU "Uj vevo,Lista,Kilepes" TO valasz TITLE "Fomenu"
DO CASE
CASE valasz = 1
  DO ujvevo()
CASE valasz = 2
  USE vevok
  BROWSE
OTHERWISE
  @ 10,10 SAY "Viszlat!"
ENDCASE
? JSONSTRING("kesz")

FUNCTION ujvevo()
  USE vevok
  APPEND BLANK
  @ 5,5 SAY "Nev:"
  @ 5,11 GET nev
  READ
  REPLACE nev WITH nev
  @ 7,5 SAY "Rogzitve: " + ALLTRIM(nev)
RETURN
