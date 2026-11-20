"""HxBase minimal PDF-iro (stdlib only): szamlak/szallitok nyomtatasahoz.

14 standard betutipus (Helvetica/Helvetica-Bold), WinAnsi kodolas.
Ekezet-transzliteracio: az o/u roviditesek (o, u) WinAnsi-ban nincsenek meg.
"""

_TR = str.maketrans({"ő": "o", "Ő": "O", "ű": "u", "Ű": "U"})


def _safe(s):
    t = str(s).translate(_TR).replace("–", "-").replace("—", "-")
    return t.encode("cp1252", "replace").decode("cp1252")


def _esc(s):
    return _safe(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PdfDoc:
    def __init__(self):
        self.ops = []  # ("title", text) | ("head", text) | ("line", text) | ("sep",) | ("page",)

    def title(self, t):
        self.ops.append(("title", str(t)))

    def head(self, t):
        self.ops.append(("head", str(t)))

    def line(self, t=""):
        self.ops.append(("line", str(t)))

    def sep(self):
        self.ops.append(("sep",))

    def page(self):
        self.ops.append(("page",))

    def build(self, path):
        pages = [[]]
        for op in self.ops:
            if op[0] == "page":
                pages.append([])
            else:
                pages[-1].append(op)
        objs = []
        # 1 katalogus, 2 lapok, 3 Helvetica, 4 Helvetica-Bold
        content_ids = []
        page_ids = []
        nxt = 5
        for pg in pages:
            cid = nxt
            nxt += 1
            content_ids.append(cid)
        for _ in pages:
            pid = nxt
            nxt += 1
            page_ids.append(pid)
        kids = " ".join(f"{p} 0 R" for p in page_ids)
        objs.append((1, "<< /Type /Catalog /Pages 2 0 R >>"))
        objs.append((2, f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>"))
        objs.append((3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"))
        objs.append((4, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"))

        def content_stream(pg):
            out = ["BT"]
            y = 800.0
            x = 50.0
            need = None
            for op in pg:
                k = op[0]
                if k == "title":
                    out.append(f"/F2 15 Tf {x:.0f} {y:.0f} Td ({_esc(op[1])}) Tj")
                    y -= 26
                elif k == "head":
                    out.append(f"/F2 11 Tf {x:.0f} {y:.0f} Td ({_esc(op[1])}) Tj")
                    y -= 17
                elif k == "line":
                    out.append(f"/F1 10 Tf {x:.0f} {y:.0f} Td ({_esc(op[1])}) Tj")
                    y -= 14
                elif k == "sep":
                    out.append("ET")
                    out.append(f"{x:.0f} {y + 4:.0f} m 545 {y + 4:.0f} l S")
                    out.append("BT")
                    y -= 10
                if y < 60:
                    break  # tulcsordulas: kovetkezo oldalra tartozna (PDFOLDAL hasznalando)
            out.append("ET")
            return "\n".join(out)

        for cid, pg in zip(content_ids, pages):
            s = content_stream(pg)
            objs.append((cid, f"<< /Length {len(s.encode('cp1252'))} >>\nstream\n{s}\nendstream"))
        for pid in page_ids:
            cid = content_ids[page_ids.index(pid)]
            objs.append((pid, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                              f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {cid} 0 R >>"))
        out = ["%PDF-1.4"]
        offs = {}
        for oid, body in sorted(objs):
            offs[oid] = sum(len(x.encode("cp1252")) + 1 for x in out)
            out.append(f"{oid} 0 obj")
            out.append(body)
            out.append("endobj")
        xref_pos = sum(len(x.encode("cp1252")) + 1 for x in out)
        n = max(offs) + 1
        out.append(f"xref\n0 {n}")
        out.append("0000000000 65535 f ")
        for i in range(1, n):
            out.append(f"{offs.get(i, 0):010d} 00000 n ")
        out.append(f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF")
        with open(path, "wb") as f:
            f.write("\n".join(out).encode("cp1252"))
        return path
