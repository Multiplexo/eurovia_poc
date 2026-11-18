#!/usr/bin/env python3
"""Vergleicht die vom Script erzeugten Gewerke-Anfragen mit den echten Anfragen.

Ergebnis: data.json (eine Zeile je Datei mit Ampel, Gruenden, Positions- und Satzvergleich).
"""
import difflib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaeb_gewerke as gg  # noqa: E402

SRC = sys.argv[1]
OUT = sys.argv[2]

PAKETE = {
    "K181_26_0272": "Straßen.NRW 03-26-0005",
    "K181_26_0312": "Stadt Münster, Weseler Straße",
    "K182_0000001098": "Stadt Gütersloh 22014",
    "K182_0000001109": "moBiel Hochbahnsteig 24009-WIS",
    "K182_0000001128": "Straßen.NRW 06-23-0031",
    "K182_26_0105": "Straßen.NRW 06-25-0079",
    "K182_26_0168": "Stadt Bielefeld, Detmolder Str.",
}


def raw_lines(path):
    raw = open(path, "rb").read()
    return [l.decode(gg.ENC) for l in raw.replace(b"\r\n", b"\n").split(b"\n") if l.strip()]


def menge(s):
    s = s.strip()
    if not s.isdigit():
        return s
    v = int(s) / 1000
    return f"{v:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fields(r):
    """Satz in benannte Felder zerlegen (Spalten nach GAEB 90)."""
    t = r[:2]
    if t == "00":
        return [("LV-Nr.", r[13:29].strip()), ("Kennung", r[62:74].strip())]
    if t == "01":
        return [("Bezeichnung", r[2:42].rstrip()), ("Erstelldatum", r[42:50]), ("Daten", r[50:74].rstrip())]
    if t in ("11",):
        return [("OZ", r[2:11]), ("Art", r[11:74].strip())]
    if t == "21":
        return [("OZ", r[2:11]), ("Kennz.", r[11:23].rstrip()), ("Menge", menge(r[23:34])),
                ("Einheit", r[34:38].strip()), ("Zusatz", r[38:74].strip())]
    if t == "27":
        return [("Zusatzdaten", r[2:74].strip())]
    if t == "99":
        return [("Kennung", r[2:69].strip()), ("Anz. Positionen", r[69:74].lstrip("0") or "0")]
    names = {"02": "Name", "03": "Auftraggeber", "08": "Währung", "12": "Titel", "20": "Vorbemerkung",
             "25": "Kurztext", "26": "Langtext", "31": "Ende OZ", "06": "Kostenarten"}
    return [(names.get(t, "Inhalt"), r[2:74].rstrip())]


SATZ = {"00": "Kopf", "01": "Bezeichnung/Datum", "02": "Name", "03": "Auftraggeber", "06": "Kostenarten",
        "08": "Währung", "11": "Gliederung", "12": "Titel", "20": "Vorbemerkung", "21": "Position",
        "25": "Kurztext", "26": "Langtext", "27": "Zusatzdaten", "31": "Gliederungsende", "99": "Dateiende"}


def items_of(path):
    _, root, _ = gg.parse(path)
    out = []
    for it in gg.iter_items(root):
        r21 = next(r for r in it.records if r[:2] == "21")
        k = it.records.index(r21)
        lang = " ".join(r[2:74].strip() for r in it.records[k:] if r[:2] == "26")
        out.append({"oz": " ".join(it.oz.split()), "kurz": it.kurztext.strip(), "menge": menge(r21[23:34]),
                    "einheit": r21[34:38].strip(), "lang": lang})
    return out


def textkey(i):
    return (i["kurz"], i["menge"], i["einheit"])


def compare(orig, gen, by_text):
    lo, ls = raw_lines(orig), (raw_lines(gen) if gen else [])
    co = [l[:74] for l in lo]
    cs = [l[:74] for l in ls]
    norm = lambda rs: [r[:42] + "########" + r[50:] if r[:2] == "01" else r for r in rs]
    gründe = []
    io = items_of(orig)
    is_ = items_of(gen) if gen else []
    key = textkey if by_text else (lambda i: i["oz"])
    mo = {}
    for i in io:
        mo.setdefault(key(i), []).append(i)
    ms = {}
    for i in is_:
        ms.setdefault(key(i), []).append(i)
    pos = []
    hart = weich = 0
    oz_abw = 0
    for k in list(dict.fromkeys(list(mo) + list(ms))):
        a, b = mo.get(k, []), ms.get(k, [])
        for n in range(max(len(a), len(b))):
            x = a[n] if n < len(a) else None
            y = b[n] if n < len(b) else None
            diff = []
            if x and y:
                for f in ("oz", "kurz", "menge", "einheit", "lang"):
                    if x[f] != y[f]:
                        diff.append(f)
            st = "ok"
            if not x or not y or set(diff) & {"kurz", "menge", "einheit"}:
                st = "hart"
                hart += 1
            elif diff:
                st = "leicht"
                weich += 1
                if "oz" in diff:
                    oz_abw += 1
            pos.append({"o": x and {k2: x[k2] for k2 in ("oz", "kurz", "menge", "einheit")},
                        "s": y and {k2: y[k2] for k2 in ("oz", "kurz", "menge", "einheit")},
                        "st": st, "diff": diff})
    fehlt = sum(1 for p in pos if not p["s"])
    zuviel = sum(1 for p in pos if not p["o"])
    if not gen:
        gründe.append("Script hat diese Datei nicht erzeugt")
    if fehlt:
        gründe.append(f"{fehlt} Positionen fehlen im Script-Ergebnis")
    if zuviel:
        gründe.append(f"{zuviel} Positionen zu viel im Script-Ergebnis")
    andere = sum(1 for p in pos if p["o"] and p["s"] and set(p["diff"]) & {"kurz", "menge", "einheit"})
    if andere:
        gründe.append(f"{andere} Positionen mit anderem Kurztext, Menge oder Einheit")
    if oz_abw:
        gründe.append(f"{oz_abw} Positionen mit anderer Ordnungszahl (Inhalt gleich)")
    lang = sum(1 for p in pos if p["st"] == "leicht" and "lang" in p["diff"])
    if lang:
        gründe.append(f"{lang} Positionen mit abweichendem Langtext")

    # Satzvergleich (ohne Zeilennummer; Erstelldatum ausgenommen)
    no, ns = norm(co), norm(cs)
    sm = difflib.SequenceMatcher(None, no, ns, autojunk=False)
    rows = []
    typ_abw = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for r in co[i1:i2] + cs[j1:j2]:
            typ_abw[r[:2]] = typ_abw.get(r[:2], 0) + 1
    ops = list(sm.get_opcodes())  # get_grouped_opcodes veraendert die gecachte Liste
    stellen = sum(1 for g in sm.get_grouped_opcodes(2) if any(op[0] != "equal" for op in g))
    for tag, i1, i2, j1, j2 in ops:
        for k in range(max(i2 - i1, j2 - j1)):
            x = co[i1 + k].rstrip() if i1 + k < i2 else None
            y = cs[j1 + k].rstrip() if j1 + k < j2 else None
            rows.append([tag[0], x] if tag == "equal" and x == y else [tag[0], x, y])
    sonst = {t: n for t, n in typ_abw.items() if t not in ("21", "25", "26", "27")}
    if sonst and gen:
        gründe.append("Abweichende Sätze: " + ", ".join(f"{SATZ.get(t, t)} ({t})" for t in sorted(sonst)))
    datum_o = next((r[42:50] for r in co if r[:2] == "01"), "")
    datum_s = next((r[42:50] for r in cs if r[:2] == "01"), "")
    if not gen or hart:
        ampel = "rot"
    elif no == ns:
        ampel = "gruen"
    else:
        ampel = "orange"
    return {"ampel": ampel, "gruende": gründe, "pos": pos, "rows": rows, "stellen": stellen, "saetze_o": len(lo), "saetze_s": len(ls),
            "datum_o": datum_o, "datum_s": datum_s, "n_pos_o": len(io), "n_pos_s": len(is_)}


def main():
    work = os.path.join(os.path.dirname(OUT) or ".", "gen")
    pakete = []
    for pk in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, pk)
        if not os.path.isdir(d):  # z. B. .DS_Store auf dem Mac
            continue
        files = sorted(f for f in os.listdir(d) if f.upper().endswith(".D83"))
        main_f = next(f for f in files if all(g == f or g.endswith("_" + f) for g in files))
        stem = os.path.splitext(main_f)[0]
        mp = os.path.join(d, main_f)
        header, root, trailer = gg.parse(mp)
        main_items = list(gg.iter_items(root))
        main_oz = {it.oz for it in main_items}
        by_text = {}
        for it in main_items:
            r21 = next(r for r in it.records if r[:2] == "21")
            by_text.setdefault((it.kurztext.strip(), r21[23:34], r21[34:38]), []).append(it.oz)
        os.makedirs(os.path.join(work, pk), exist_ok=True)
        dateien = []
        oz_hits = 0
        gfiles = [f for f in files if f != main_f]
        sels = {}
        for f in gfiles:
            gp = os.path.join(d, f)
            hdr, groot, _ = gg.parse(gp)
            name = next((r[2:74].strip() for r in hdr if r[:2] == "02"), "")
            sel, ozok = set(), 0
            for it in gg.iter_items(groot):
                if it.oz in main_oz:
                    ozok += 1
                    sel.add(it.oz)
            sels[f] = (name, sel, ozok, len(list(gg.iter_items(groot))), groot)
        # Paket mit anderer Nummerierung: ueber Kurztext + Menge + Einheit zuordnen
        total = sum(v[3] for v in sels.values())
        hits = sum(v[2] for v in sels.values())
        text_mode = hits < total * 0.5
        for f in gfiles:
            name, sel, _, _, groot = sels[f]
            if text_mode:
                sel = set()
                for it in gg.iter_items(groot):
                    r21 = next(r for r in it.records if r[:2] == "21")
                    for oz in by_text.get((it.kurztext.strip(), r21[23:34], r21[34:38]), []):
                        sel.add(oz)
            code = gg.gewerk_code(f, main_f)
            gen = None
            if sel:
                txt = gg.build(header, root, trailer, name or code, sel, None)
                gen = os.path.join(work, pk, f)
                open(gen, "wb").write(txt.encode(gg.ENC, errors="replace"))
            r = compare(os.path.join(d, f), gen, text_mode)
            r.update({"datei": f, "code": code, "name": name})
            dateien.append(r)
        pakete.append({"id": pk, "titel": PAKETE.get(pk, pk), "lv": main_f, "textmodus": text_mode,
                       "dateien": dateien})
        print(pk, text_mode, {a: sum(1 for x in dateien if x["ampel"] == a) for a in ("gruen", "orange", "rot")})
    json.dump(pakete, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


main()
