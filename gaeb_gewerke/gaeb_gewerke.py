#!/usr/bin/env python3
"""Gewerke-Anfragen (GAEB 90, DA 83) aus einem Gesamt-LV erzeugen.

Ein Gesamt-LV (.D83) wird anhand einer Zuordnung "Gewerk -> Positionen" in
einzelne Anfrage-Dateien zerlegt, so wie sie die Kalkulation fuer
Nachunternehmer und Lieferanten exportiert (z. B. MARK_<LV>.D83).

  extract  Zuordnung aus vorhandenen Gewerke-Dateien auslesen (JSON)
  split    Gewerke-Dateien aus Gesamt-LV + Zuordnung erzeugen

Beispiele:
  python3 gaeb_gewerke.py extract 06-25-0079.D83 MARK_06-25-0079.D83 VS_06-25-0079.D83 -o zuordnung.json
  python3 gaeb_gewerke.py split 06-25-0079.D83 zuordnung.json -o anfragen/
"""
import argparse
import datetime
import json
import os
import sys

ENC = "cp850"


# ---------------------------------------------------------------- Einlesen

def read_records(path):
    raw = open(path, "rb").read()
    lines = [l.decode(ENC) for l in raw.replace(b"\r\n", b"\n").split(b"\n") if l.strip()]
    # T0..T9-Block (z. B. Baubeschreibung) vor dem 00er-Satz wird nicht mit angefragt
    start = next((i for i, l in enumerate(lines) if l[:2] == "00"), 0)
    lines = lines[start:]
    # 06er-Satz = Kostenarten der Kalkulation: dann sind die 27er-Saetze
    # interne Kalkulationsansaetze und gehoeren nicht in die Anfrage
    if any(l[:2] == "06" for l in lines):
        lines = [l for l in lines if l[:2] not in ("06", "27")]
        # Kennzeichen in Spalte 19 des 21er-Satzes ("X") stammt ebenfalls aus der Kalkulation
        lines = [l[:18] + " " + l[19:] if l[:2] == "21" else l for l in lines]
    return lines


def rtype(r):
    return r[:2]


def oz_of(r):
    """OZ-Feld eines 21er-Satzes (Spalten 3-11)."""
    return r[2:11]


class Item:
    """Eine Position: optionale Vorbemerkung (20er-Block) + 21er-Satz + Folgesaetze."""

    def __init__(self, pre):
        self.records = list(pre)
        self.oz = None
        self.kurztext = ""

    def add(self, r):
        if rtype(r) == "21":
            self.oz = oz_of(r)
        elif rtype(r) == "25" and self.oz is not None:
            self.kurztext += r[2:74].strip() + " "
        self.records.append(r)


class Group:
    def __init__(self, records):
        self.open = list(records)   # 11er + 12er
        self.children = []
        self.tail = []              # 20er-Block direkt vor dem 31er (wird nicht exportiert)
        self.close = None           # 31er


def parse(path):
    recs = read_records(path)
    header, root, stack, trailer = [], Group([]), [], None
    stack.append(root)
    pending_pre = []          # 20er-Block, gehoert zur naechsten Position
    cur_item = None
    i = 0
    while i < len(recs):
        r = recs[i]
        t = rtype(r)
        if t == "99":
            trailer = r
        elif t in ("11",):
            cur_item = None
            g = Group(pending_pre + [r])
            pending_pre = []
            while i + 1 < len(recs) and rtype(recs[i + 1]) == "12":
                i += 1
                g.open.append(recs[i])
            stack[-1].children.append(g)
            stack.append(g)
        elif t == "31":
            cur_item = None
            # 20er-Block direkt vor Gruppenende gehoert zu keiner Position und
            # wird (wie in den Original-Anfragen) nur im Gesamt-LV gefuehrt
            stack[-1].tail, pending_pre = pending_pre, []
            stack[-1].close = r
            stack.pop()
        elif t == "20":
            cur_item = None
            pending_pre.append(r)
        elif t == "21":
            cur_item = Item(pending_pre)
            pending_pre = []
            cur_item.add(r)
            stack[-1].children.append(cur_item)
        elif cur_item is not None:
            cur_item.add(r)
        elif pending_pre:
            pending_pre.append(r)
        elif not root.children:
            header.append(r)
        else:
            raise ValueError(f"{path}: unerwarteter Satz {t} in Zeile {i + 1}")
        i += 1
    return header, root, trailer


def iter_items(group):
    for c in group.children:
        if isinstance(c, Item):
            yield c
        else:
            yield from iter_items(c)


# ---------------------------------------------------------------- Schreiben

def with_text(r, text):
    """Datenteil (Spalten 3-74) eines Satzes ersetzen."""
    return r[:2] + text[:72].ljust(72) + r[74:]


def emit(group, selected, out):
    """Schreibt Gruppe rekursiv, nur Zweige mit ausgewaehlten Positionen."""
    body = []
    for c in group.children:
        if isinstance(c, Item):
            if c.oz in selected:
                body.extend(c.records)
        else:
            body.extend(emit(c, selected, []))
    if not body:
        return out
    out.extend(group.open)
    out.extend(body)
    if group.close:
        out.append(group.close)
    return out


def build(header, root, trailer, name, selected, datum=None):
    hdr = []
    for r in header:
        if rtype(r) == "02":
            r = with_text(r, name)
        elif rtype(r) == "01" and datum:
            r = r[:42] + datum + r[50:]
        hdr.append(r)
    body = emit(root, selected, [])
    lines = [r[:74] for r in hdr + body]
    n_pos = sum(1 for r in lines if rtype(r) == "21")
    out = [r.ljust(74) + f"{i + 1:06d}" for i, r in enumerate(lines)]
    if trailer is not None:
        t = trailer[:69].ljust(69) + f"{n_pos:05d}{len(out) + 1:06d}"
        out.append(t)
    return "\r\n".join(out) + "\r\n"


# ---------------------------------------------------------------- Befehle

def gewerk_code(path, main_path):
    """'MARK_06-25-0079.D83' -> 'MARK'."""
    base = os.path.basename(path)
    stem = os.path.splitext(os.path.basename(main_path))[0]
    suffix = "_" + stem
    s = os.path.splitext(base)[0]
    return s[: -len(suffix)] if s.endswith(suffix) else s.split("_")[0]


def cmd_extract(a):
    _, mroot, _ = parse(a.main)
    main_oz = {it.oz for it in iter_items(mroot)}
    gewerke = []
    for p in a.gewerke:
        hdr, root, _ = parse(p)
        name = next((r[2:74].strip() for r in hdr if rtype(r) == "02"), "")
        oz, fehlt = [], 0
        for it in iter_items(root):
            if it.oz in main_oz:
                oz.append(it.oz)
            else:
                fehlt += 1
        if fehlt:
            print(f"WARNUNG {os.path.basename(p)}: {fehlt} Positionen nicht per OZ im Gesamt-LV gefunden",
                  file=sys.stderr)
        gewerke.append({"code": gewerk_code(p, a.main), "name": name,
                        "oz": [o.strip() for o in oz]})
    res = {"lv": os.path.basename(a.main), "gewerke": gewerke}
    out = open(a.output, "w", encoding="utf-8") if a.output else sys.stdout
    json.dump(res, out, ensure_ascii=False, indent=1)


def norm(oz):
    return " ".join(oz.split())


def cmd_split(a):
    header, root, trailer = parse(a.main)
    items = list(iter_items(root))
    by_norm = {norm(it.oz): it.oz for it in items}
    cfg = json.load(open(a.zuordnung, encoding="utf-8"))
    stem = os.path.splitext(os.path.basename(a.main))[0]
    ext = os.path.splitext(a.main)[1] or ".D83"
    datum = a.datum or datetime.date.today().strftime("%d.%m.%y")
    if a.datum == "lv":
        datum = None
    os.makedirs(a.output, exist_ok=True)
    for g in cfg["gewerke"]:
        sel = set()
        for o in g["oz"]:
            if norm(o) in by_norm:
                sel.add(by_norm[norm(o)])
            else:
                print(f"WARNUNG {g['code']}: OZ {o!r} nicht im LV", file=sys.stderr)
        if not sel:
            continue
        txt = build(header, root, trailer, g.get("name") or g["code"], sel, datum)
        path = os.path.join(a.output, f"{g['code']}_{stem}{ext}")
        with open(path, "wb") as f:
            f.write(txt.encode(ENC, errors="replace"))
        print(f"{path}: {len(sel)} Positionen")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="Zuordnung aus vorhandenen Gewerke-Dateien lesen")
    e.add_argument("main")
    e.add_argument("gewerke", nargs="+")
    e.add_argument("-o", "--output")
    s = sub.add_parser("split", help="Gewerke-Dateien erzeugen")
    s.add_argument("main")
    s.add_argument("zuordnung")
    s.add_argument("-o", "--output", default="gewerke")
    s.add_argument("--datum", help="Erstelldatum TT.MM.JJ im 01er-Satz (Standard: heute, 'lv' = aus LV uebernehmen)")
    a = ap.parse_args()
    {"extract": cmd_extract, "split": cmd_split}[a.cmd](a)


if __name__ == "__main__":
    main()
