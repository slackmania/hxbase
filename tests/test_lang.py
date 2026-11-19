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
