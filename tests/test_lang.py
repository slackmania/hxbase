"""HxBase tesztek: parser + VM headless + SQLite."""
import os
import tempfile

from hxbase.compiler import compile_source
from hxbase.db import DBManager
from hxbase.screen import HeadlessScreen
from hxbase.vm import VM


def run(src, inputs=None):
    tmp = tempfile.mkdtemp()
    sc = HeadlessScreen()
    if inputs:
        sc.inputs = {k.upper(): v for k, v in inputs.items()}
    dbm = DBManager(tmp)
    vm = VM(sc, dbm, tmp)
    vm.run_code(compile_source(src)["code"])
    dbm.close_all()
    return sc, vm


def test_if_for():
    sc, vm = run('''
x = 0
FOR i = 1 TO 5
  x = x + i
NEXT
IF x = 15
  @ 1,1 SAY "OK15"
ELSE
  @ 1,1 SAY "ROSSZ"
ENDIF
''')
    assert "OK15" in sc.dump(), sc.dump()


def test_while_func():
    sc, vm = run('''
n = 0
s = 0
DO WHILE n < 4
  n = n + 1
  s = s + n * 2
ENDDO
@ 1,1 SAY STR(s)
DO hello("Vilag")
FUNCTION hello(nev)
  @ 2,1 SAY "Hi " + nev
RETURN
''')
    d = sc.dump()
    assert "20" in d and "Hi Vilag" in d, d


def test_db_locate():
    sc, vm = run('''
CREATE t (nev C(20), kor N(3))
USE t
APPEND BLANK
REPLACE nev WITH "A", kor WITH 10
APPEND BLANK
REPLACE nev WITH "B", kor WITH 50
LOCATE FOR kor > 20
@ 1,1 SAY ALLTRIM(nev)
CONTINUE
''')
    assert "B" in sc.dump(), sc.dump()


def test_pcode_roundtrip():
    import json
    src = '? "hello " + UPPER("vilag")'
    code = compile_source(src)
    s2 = json.loads(json.dumps(code))
    sc, vm = run(src)
    assert "VILAG" in " ".join(sc.lists).upper()


def test_widgets_headless():
    sc, vm = run('''
w_nev = ""
w_hir = .F.
w_fiz = 1
''', inputs={"W_NEV": "anna", "W_HIR": ".T.", "W_FIZ": "3"})
    src = '''
CLEAR
@ 1,1 GET w_nev PICTURE "@!"
@ 2,1 CHECKBOX w_hir PROMPT "Hirlevel"
@ 3,1 RADIO w_fiz OPTIONS "a,b,c" TITLE "Valasz"
@ 4,1 BUTTON "OK" ACTION kesz()
READ
@ 5,1 SAY w_nev
FUNCTION kesz()
RETURN
'''
    sc2 = HeadlessScreen()
    sc2.inputs = {"W_NEV": "anna", "W_HIR": ".T.", "W_FIZ": "3"}
    import tempfile
    from hxbase.db import DBManager
    from hxbase.vm import VM
    dbm = DBManager(tempfile.mkdtemp())
    vm2 = VM(sc2, dbm, ".")
    vm2.run_code(compile_source(src)["code"])
    assert vm2.mem["W_NEV"] == "ANNA"
    assert vm2.mem["W_HIR"] is True
    assert vm2.mem["W_FIZ"] == 3
    assert "[X] Hirlevel" in sc2.dump()


def test_sum_count_sort():
    sc, vm = run('''
CREATE t (nev C(10), kor N(3))
USE t
FOR i = 1 TO 4
  APPEND BLANK
  REPLACE nev WITH "N" + STR(i), kor WITH i * 10
NEXT
SUM kor TO s
AVERAGE kor TO a
COUNT TO c FOR kor > 15
''')
    assert vm.mem["S"] == 100.0
    assert vm.mem["A"] == 25.0
    assert vm.mem["C"] == 3


def test_box_save_restore():
    from hxbase.screen import HeadlessScreen
    sc = HeadlessScreen()
    sc.say(10, 10, "HATTER")
    saved = sc.save_region(9, 9, 12, 20)
    sc.draw_box(9, 9, 12, 20, "Ablak")
    assert sc.buf[9][9] == "┌" and sc.buf[12][20] == "┘"
    sc.restore_region(saved)
    assert sc.text_row(10) == " " * 10 + "HATTER"


def test_new_funcs():
    sc, vm = run('''
x = TRANSFORM(1234.5, "999,999.99")
y = REPLICATE("ab", 3) + SPACE(1) + PADL("7", 3, "0")
z = STUFF("abcdef", 2, 3, "XY") + STR(RAT("n", "anna"))
t = VALTYPE("s") + VALTYPE(1) + VALTYPE(.T.)
@ 1,1 SAY x
@ 2,1 SAY y
@ 3,1 SAY z
@ 4,1 SAY t
''')
    d = sc.dump()
    assert "1,234.50" in d and "ababab 007" in d and "aXYef3" in d and "CNL" in d
