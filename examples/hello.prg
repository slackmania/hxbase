* HxBase demo 1: hello + kepernyo + valtozok
CLEAR
@ 2,10 SAY "HXBASE - Clipper ihletesu demo" COLOR "W/B"
@ 4,10 SAY "Nev:"
@ 4,16 GET nev
@ 5,10 SAY "Kor:"
@ 5,16 GET kor
READ
@ 7,10 SAY "Hello, " + ALLTRIM(nev) + "! " + STR(kor) + " eves vagy."
@ 8,10 SAY "Datum: " + DATE() + "  Ido: " + TIME()
? "Valtozok keszen."
