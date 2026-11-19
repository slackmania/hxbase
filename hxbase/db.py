"""HxBase DB: SQLite alapu workarea-kezelas DBF szemantikaval."""

import os
import re
import sqlite3

FIELD_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+([CNDLM])\s*(?:\(\s*(\d+)(?:\s*,\s*(\d+))?\s*\))?\s*$", re.I)

SQLITE_TYPE = {"C": "TEXT", "M": "TEXT", "D": "TEXT", "L": "INTEGER", "N": "REAL"}


def parse_field_defs(defs_str):
    """'NEV C(30), KOR N(3,0), SZUL D, AKTIV L' -> [(nev,tipus,hossz,tizedes)]"""
    out = []
    for part in defs_str.split(","):
        part = part.strip()
        if not part:
            continue
        m = FIELD_RE.match(part)
        if not m:
            raise ValueError(f"Hibas mezodefinicio: {part!r} (pelda: NEV C(30))")
        name, typ, ln, dc = m.group(1).upper(), m.group(2).upper(), m.group(3), m.group(4)
        out.append((name, typ, int(ln) if ln else {"C": 30, "M": 30, "D": 10, "L": 1, "N": 10}[typ], int(dc) if dc else 0))
    if not out:
        raise ValueError("Ures mezolista")
    return out


class WorkArea:
    def __init__(self, alias, db_path, table):
        self.alias = alias.upper()
        self.db_path = db_path
        self.table = table
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.fields = []  # [(name,typ,len,dec)]
        self.order = []   # [(recno,rowdict)]
        self.pos = -1
        self.eof = True
        self.bof = True
        self.filter_ast = None
        self._load_schema()
        self.refresh()

    def _load_schema(self):
        cur = self.conn.execute(f'PRAGMA table_info("{self.table}")')
        cols = [dict(r) for r in cur.fetchall()]
        # valodi szelessegek a meta-tablabol (CREATE-kor mentve)
        meta = {}
        try:
            names = [x[0] for x in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "_hxmeta" in names:
                try:
                    for r in self.conn.execute('SELECT field, typ, w, d FROM "_hxmeta"'):
                        meta[r[0]] = (r[1], r[2], r[3])
                except Exception:
                    for r in self.conn.execute('SELECT field, w, d FROM "_hxmeta"'):
                        meta[r[0]] = ("C", r[1], r[2])
        except Exception:
            meta = {}
        # _recno,_deleted kihagyasa
        for c in cols:
            n = c["name"]
            if n in ("_recno", "_deleted", "_hxmeta"):
                continue
            if n in meta:
                typ, w, d = meta[n]
                self.fields.append((n.upper(), typ, w, d))
                continue
            t = c["type"].upper()
            typ = "C" if t == "TEXT" else "N"
            if n in meta:
                w, d = meta[n]
            else:
                w, d = (30, 0)
            self.fields.append((n.upper(), typ, w, d))

    def column_names(self):
        return [f[0] for f in self.fields]

    def refresh(self):
        cur = self.conn.execute(f'SELECT * FROM "{self.table}" ORDER BY _recno')
        rows = [dict(r) for r in cur.fetchall()]
        self.order = [(r["_recno"], r) for r in rows]
        if not self.order:
            self.pos = -1
            self.eof = True
            self.bof = True
        else:
            if self.pos < 0:
                self.pos = 0
            self.pos = max(0, min(self.pos, len(self.order) - 1))
            self._update_flags()

    def _update_flags(self):
        if not self.order or self.pos < 0 or self.pos >= len(self.order):
            self.eof = True
            self.bof = True
        else:
            self.eof = False
            self.bof = False

    def current(self):
        if not self.order or self.pos < 0 or self.pos >= len(self.order):
            return None
        return self.order[self.pos][1]

    def recno(self):
        c = self.current()
        return c["_recno"] if c else 0

    def reccount(self):
        return len(self.order)

    # --- mozgas ---
    def go_top(self):
        self.refresh()
        self.pos = 0 if self.order else -1
        self._update_flags()

    def go_bottom(self):
        self.refresh()
        self.pos = len(self.order) - 1 if self.order else -1
        self._update_flags()

    def go(self, n):
        self.refresh()
        idx = None
        for i, (recno, _) in enumerate(self.order):
            if recno == n:
                idx = i
                break
        if idx is None:
            self.pos = len(self.order)
            self.eof = True
        else:
            self.pos = idx
            self._update_flags()

    def skip(self, n=1):
        if not self.order:
            self.eof = True
            return
        self.pos += n
        if self.pos >= len(self.order):
            self.pos = len(self.order)
            self.eof = True
        elif self.pos < 0:
            self.pos = -1
            self.bof = True
        else:
            self._update_flags()

    # --- iras ---
    def append_blank(self):
        cur = self.conn.execute(f'INSERT INTO "{self.table}" DEFAULT VALUES')
        self.conn.commit()
        self.refresh()
        self.pos = len(self.order) - 1
        self._update_flags()

    def replace(self, field, value):
        c = self.current()
        if c is None:
            raise RuntimeError("Nincs aktualis rekord (ures tabla? APPEND BLANK kell)")
        field = field.upper()
        if field not in self.column_names() and field not in ("_DELETED", "DELETED"):
            raise RuntimeError(f"Nincs ilyen mezo: {field}")
        col = "_deleted" if field in ("_DELETED", "DELETED") else field
        if isinstance(value, bool):
            value = 1 if value else 0
        self.conn.execute(f'UPDATE "{self.table}" SET "{col}"=? WHERE _recno=?', (value, c["_recno"]))
        self.conn.commit()
        self.refresh_keep(c["_recno"])

    def refresh_keep(self, recno):
        self.refresh()
        self.go(recno)

    def delete_current(self):
        c = self.current()
        if c:
            self.conn.execute(f'UPDATE "{self.table}" SET _deleted=1 WHERE _recno=?', (c["_recno"],))
            self.conn.commit()

    def recall_current(self):
        c = self.current()
        if c:
            self.conn.execute(f'UPDATE "{self.table}" SET _deleted=0 WHERE _recno=?', (c["_recno"],))
            self.conn.commit()

    def pack(self):
        self.conn.execute(f'DELETE FROM "{self.table}" WHERE _deleted=1')
        self.conn.commit()
        self.refresh()

    def zap(self):
        self.conn.execute(f'DELETE FROM "{self.table}"')
        self.conn.commit()
        self.refresh()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


class DBManager:
    def __init__(self, base_dir="."):
        self.base_dir = base_dir or "."
        os.makedirs(self.base_dir, exist_ok=True)
        self.areas = []  # WorkArea list
        self.current = -1
        self.alias_map = {}  # alias -> idx

    def _resolve(self, name):
        name = name.strip().strip('"').strip("'")
        if os.path.isabs(name):
            return name
        base = os.path.splitext(os.path.basename(name))[0]
        if "." in os.path.basename(name) and name.lower().endswith((".db", ".sqlite", ".dbf")):
            return name if os.path.isabs(name) else os.path.join(self.base_dir, os.path.basename(name))
        return os.path.join(self.base_dir, base + ".db")

    def create_table(self, name, field_defs):
        base = os.path.splitext(os.path.basename(name.strip()))[0]
        db_path = os.path.join(self.base_dir, base + ".db")
        table = base
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = sqlite3.connect(db_path)
        cols = ['_recno INTEGER PRIMARY KEY AUTOINCREMENT', '_deleted INTEGER DEFAULT 0']
        for (fname, typ, ln, dc) in field_defs:
            cols.append(f'"{fname}" {SQLITE_TYPE[typ]}')
        conn.execute(f'CREATE TABLE "{table}" ({", ".join(cols)})')
        conn.execute('DROP TABLE IF EXISTS "_hxmeta"')
        conn.execute('CREATE TABLE "_hxmeta" (field TEXT PRIMARY KEY, typ TEXT, w INTEGER, d INTEGER)')
        for (fname, typ, ln, dc) in field_defs:
            conn.execute('INSERT OR REPLACE INTO "_hxmeta" (field, typ, w, d) VALUES (?,?,?,?)', (fname, typ, ln, dc))
        conn.commit()
        conn.close()
        return db_path

    def use(self, name=None, alias=None):
        if name is None or str(name).strip() == "":
            self.close_current()
            return None
        db_path = self._resolve(str(name))
        if not os.path.exists(db_path):
            raise RuntimeError(f"Nem talalhato adatbazis: {db_path} (elozo CREATE kell)")
        base = os.path.splitext(os.path.basename(db_path))[0]
        table = base
        # tabla letezik?
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        if table not in tables:
            # ha mas nevu tabla van, elso tablat nyitjuk
            if tables:
                table = tables[0]
            else:
                raise RuntimeError(f"Nincs tabla itt: {db_path}")
        al = (alias or base).upper()
        area = WorkArea(al, db_path, table)
        self.areas.append(area)
        self.current = len(self.areas) - 1
        self.alias_map[al] = self.current
        return area

    def close_current(self):
        if 0 <= self.current < len(self.areas):
            try:
                self.areas[self.current].close()
            except Exception:
                pass
            al = self.areas[self.current].alias
            self.areas.pop(self.current)
            self.alias_map = {a.alias.upper(): i for i, a in enumerate(self.areas)}
            self.current = len(self.areas) - 1 if self.areas else -1

    def close_all(self):
        for a in self.areas:
            try:
                a.close()
            except Exception:
                pass
        self.areas = []
        self.current = -1
        self.alias_map = {}

    def cur(self):
        if 0 <= self.current < len(self.areas):
            return self.areas[self.current]
        return None

    def select(self, which):
        if isinstance(which, int) or (isinstance(which, str) and which.strip().isdigit()):
            i = int(which) - 1
            if 0 <= i < len(self.areas):
                self.current = i
                return self.cur()
            raise RuntimeError(f"Nincs ilyen workarea: {which}")
        al = str(which).strip().upper()
        if al in self.alias_map:
            self.current = self.alias_map[al]
            return self.cur()
        raise RuntimeError(f"Nincs ilyen alias: {which}")

    def field_value(self, field, alias=None):
        field = field.upper()
        area = self.cur() if alias is None else self.areas[self.alias_map[alias.upper()]]
        if area is None:
            raise RuntimeError("Nincs nyitott tabla (USE kell)")
        c = area.current()
        if c is None:
            return "" if field not in ("_DELETED", "DELETED") else False
        if field in ("_DELETED", "DELETED", "DELETED()"):
            return bool(c.get("_deleted", 0))
        # sqlite oszlopnevek eredeti case-ben lehetnek; probalkozunk case-insensitive
        for k, v in c.items():
            if k.upper() == field:
                return v if v is not None else ""
        raise RuntimeError(f"Nincs ilyen mezo: {field}")

    def set_field(self, field, value):
        area = self.cur()
        if area is None:
            raise RuntimeError("Nincs nyitott tabla")
        area.replace(field, value)
