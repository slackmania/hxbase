* BEVITEL - kezi adatbevitel pozicionalt SAY/GET-tel a teszt50-be
CLEAR
@ 2,10 SAY "BEVITEL - teszt50 kezi bovites" COLOR "W/B"
CLOSE ALL
TRY
  USE teszt50
CATCH
  CREATE teszt50 (kod N(3), nev C(30), kor N(3), aktiv L)
  USE teszt50
ENDTRY
@ 4,10 SAY "Jelenlegi sorok: " + STR(RECCOUNT())
DO WHILE .T.
  m_kod = RECCOUNT() + 1
  m_nev = ""
  m_kor = 30
  m_aktiv = .T.
  @ 6,10 SAY "Kod:"
  @ 6,16 SAY m_kod
  @ 7,10 SAY "Nev:"
  @ 7,16 GET m_nev
  @ 8,10 SAY "Kor:"
  @ 8,16 GET m_kor
  @ 9,10 SAY "Aktiv (.T./.F.):"
  @ 9,28 GET m_aktiv
  READ
  IF EMPTY(m_nev)
    @ 11,10 SAY "Ures nev - nem rogzitem."
  ELSE
    APPEND BLANK
    REPLACE kod WITH m_kod, nev WITH m_nev, kor WITH m_kor, aktiv WITH m_aktiv
    @ 11,10 SAY "Rogzitve: " + ALLTRIM(m_nev)
  ENDIF
  @ 13,10 SAY "Meg egy? (I/N)"
  @ 13,24 GET m_meg
  READ
  IF UPPER(m_meg) <> "I"
    EXIT
  ENDIF
ENDDO
@ 15,10 SAY "Osszes sor: " + STR(RECCOUNT())
BROWSE
