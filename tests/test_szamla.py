"""HxBase szamlazo e2e: vevo -> cikk -> bevet -> szallito -> szamla -> PDF -> storno."""
import os
import sqlite3
import tempfile
from datetime import date

from hxbase.compiler import compile_source
from hxbase.db import DBManager
from hxbase.screen import HeadlessScreen
from hxbase.vm import VM

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "szamla", "szamla.prg")
YEAR = str(date.today().year)
SZALL_NO = f"SZ-{YEAR}/000001"
SZAMLA_NO = f"yxas-{YEAR}/000001"
STORNO_NO = f"yxas-{YEAR}/000002"

DRIVER = """
DO adatbazis()
DO vevo_fel()
DO cikk_fel()
DO bevet()
DO szall_uj()
DO szall_pdf()
DO szamla_keszit()
DO szamla_pdf()
DO szamla_storno()
DO szamla_pdf()
DO szamla_storno()
DO szamla_keszit()
"""

INPUTS = {
    "M_KOD": ["C00001"],
    "M_NEV": ["Teszt Vevo Kft", "Teszt Cikk"],
    "M_CIM": ["1234 Budapest, Fo u. 1."],
    "M_ADO": ["12345678-1-11"],
    "M_ME": ["db"],
    "M_ELAD": ["1000"],
    "M_AFA": ["27"],
    "M_MENNY": ["10", "2"],
    "M_AR": ["800"],
    "M_VEVO": ["V00001"],
    "M_MEGJ": ["teszt szallitas"],
    "M_CIKK": ["C00001"],
    "M_FIZMOD": ["Atutalas", "Atutalas"],
    "M_SZALL": ["", SZALL_NO],
    "M_SZAM": ["", "", STORNO_NO],
    "M_EREDETI": ["", SZAMLA_NO],
}


def run_flow():
    tmp = tempfile.mkdtemp()
    with open(APP, encoding="utf-8") as f:
        src = f.read()
    # csak a fuggvenydefiniciok + driver (a top-level DO fomenu() menut nem futtatjuk headless-ben)
    idx = src.find("\nFUNCTION ")
    assert idx > 0
    src = src[idx + 1:] + DRIVER
    sc = HeadlessScreen()
    sc.inputs = {k: list(v) for k, v in INPUTS.items()}
    dbm = DBManager(tmp)
    vm = VM(sc, dbm, tmp)
    vm.run_code(compile_source(src)["code"])
    dbm.close_all()
    return tmp, sc


def q(tmp, db, sql):
    c = sqlite3.connect(os.path.join(tmp, db))
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_szamla_flow():
    tmp, sc = run_flow()
    # vevo + cikk + sulyozott atlagar (10 db * 800)
    assert q(tmp, "vevo.db", "SELECT kod, nev FROM vevo") == [("V00001", "Teszt Vevo Kft")]
    cikk = q(tmp, "cikk.db", "SELECT kod, keszlet, atlagar, eladar, afa FROM cikk")
    assert len(cikk) == 1
    assert cikk[0][0] == "C00001"
    assert cikk[0][2] == 800.0  # sulyozott atlagar
    # szallito: szamlazva, osszeg 2*1000
    sz = q(tmp, "szall.db", "SELECT szam, szamlazva, osszeg FROM szall")
    assert sz == [(SZALL_NO, 1, 2000.0)], sz
    # szamla + storno
    szl = q(tmp, "szamla.db", "SELECT szam, tipus, netto, afa, brutto, stornozva FROM szamla ORDER BY szam")
    assert szl == [(SZAMLA_NO, "SZAMLA", 2000.0, 540.0, 2540.0, 1),
                   (STORNO_NO, "STORNO", -2000.0, -540.0, -2540.0, 0)], szl
    # dupla storno + dupla szamlazas nem hozott letre uj sort
    assert len(szl) == 2
    # eredeti megjelolve
    assert q(tmp, "szamla.db", f"SELECT stornozva FROM szamla WHERE szam='{SZAMLA_NO}'") == [(1,)]
    # keszlet vissza: 10 - 2 + 2
    assert q(tmp, "cikk.db", "SELECT keszlet FROM cikk") == [(10.0,)]
    # sorszamok
    assert q(tmp, "sorszam.db", "SELECT tip, utolso FROM sorszam ORDER BY tip") == [("C", 1), ("S", 2), ("V", 1), ("Z", 1)]
    # PDF-ek
    for name in ("yxas-" + YEAR + "-000001.pdf", "yxas-" + YEAR + "-000002.pdf", "SZ-" + YEAR + "-000001.pdf"):
        p = os.path.join(tmp, name)
        assert os.path.exists(p), name
        with open(p, "rb") as f:
            head = f.read(5)
        assert head == b"%PDF-", name
    # szamla PDF tartalma
    with open(os.path.join(tmp, "yxas-" + YEAR + "-000001.pdf"), "rb") as f:
        pdf = f.read().decode("cp1252", "replace")
    assert "yxas-" in pdf and "2 540,00" in pdf
