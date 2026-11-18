// GAEB DA XML (X83) lesen und Gewerke-Anfragen als X83 schreiben.
// Liefert dieselbe Struktur wie GAEB.parse (items, root, info), damit die Oberfläche beide Formate gleich behandelt.
const X83 = (() => {
  const kid = (el, n) => el && [...el.children].find(c => c.localName === n);
  const path = (el, ...ns) => ns.reduce((e, n) => kid(e, n), el);
  const desc = (el, n) => el && el.getElementsByTagNameNS('*', n)[0];
  const txt = el => el ? el.textContent.replace(/\s+/g, ' ').trim() : '';

  function parse(text) {
    const doc = new DOMParser().parseFromString(text, 'application/xml');
    if (doc.getElementsByTagName('parsererror').length) throw new Error('kein gültiges GAEB-XML');
    const award = path(doc.documentElement, 'Award'), boq = kid(award, 'BoQ');
    if (!boq) throw new Error('kein Leistungsverzeichnis (BoQ) gefunden');
    const root = { children: [], title: '' }, items = [];
    (function walk(body, g, prefix) {
      for (const c of body ? body.children : []) {
        if (c.localName === 'BoQCtgy') {
          const ng = { children: [], title: txt(kid(c, 'LblTx')), parent: g };
          g.children.push(ng);
          walk(kid(c, 'BoQBody'), ng, [...prefix, c.getAttribute('RNoPart')]);
        } else if (c.localName === 'Itemlist') {
          for (const it of c.children) {
            if (it.localName !== 'Item') continue;
            const ct = desc(it, 'CompleteText'), lang = txt(desc(ct, 'DetailTxt')), q = txt(kid(it, 'Qty'));
            const stl = txt(desc(it, 'StLNo')).replace(/\D/g, '');
            const x = {
              records: [], el: it, oz: [...prefix, it.getAttribute('RNoPart')].join('.'),
              kurztext: txt(desc(ct, 'OutlineText')) || lang.slice(0, 70), langtext: lang,
              menge: q, mengeNum: parseFloat(q) || 0, einheit: txt(kid(it, 'QU')),
              // in D83 steht vor der StLK-Nummer noch eine Kennziffer (2), damit die Katalog-Regeln für beide passen
              kat: stl ? '2' + stl : '', group: g,
            };
            g.children.push(x); items.push(x);
          }
        }
      }
    })(kid(boq, 'BoQBody'), root, []);
    const adr = path(award, 'OWN', 'Address');
    const info = {
      lv: txt(path(boq, 'BoQInfo', 'Name')), bezeichnung: txt(path(boq, 'BoQInfo', 'LblBoQ')),
      name: txt(kid(adr, 'Name1')), auftraggeber: ['Name2', 'Name3'].map(n => txt(kid(adr, n))).filter(Boolean).join(' ') || txt(kid(adr, 'Name1')),
    };
    return { format: 'x83', doc, root, items, info };
  }

  // Kopie des LV, die nur die gewählten Positionen enthält. name ersetzt den Empfänger (wie 02er-Satz in D83).
  function build(lv, name, ozSet, isoDate) {
    const doc = lv.doc.cloneNode(true);
    const orig = [...lv.doc.getElementsByTagNameNS('*', 'Item')], copy = [...doc.getElementsByTagNameNS('*', 'Item')];
    const keep = new Set(lv.items.filter(it => ozSet.has(it.oz)).map(it => copy[orig.indexOf(it.el)]));
    for (const lst of [...doc.getElementsByTagNameNS('*', 'Itemlist')]) {
      // Vorbemerkung (Remark) gehört zur nächsten Position, wie der 20er-Block in D83
      let pend = [];
      for (const c of [...lst.children]) {
        if (c.localName === 'Remark') pend.push(c);
        else if (c.localName === 'Item') {
          if (!keep.has(c)) { pend.forEach(r => r.remove()); c.remove(); }
          pend = [];
        }
      }
      pend.forEach(r => r.remove());
      if (!lst.getElementsByTagNameNS('*', 'Item').length) lst.remove();
    }
    // leere Abschnitte entfernen, innen zuerst
    for (const g of [...doc.getElementsByTagNameNS('*', 'BoQCtgy')].reverse())
      if (!g.getElementsByTagNameNS('*', 'Item').length) g.remove();
    const award = path(doc.documentElement, 'Award');
    const n1 = path(award, 'OWN', 'Address', 'Name1');
    if (n1) n1.textContent = name;
    if (isoDate) [path(doc.documentElement, 'GAEBInfo', 'Date'), path(award, 'BoQ', 'BoQInfo', 'Date')]
      .forEach(d => { if (d) d.textContent = isoDate; });
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(doc.documentElement) + '\n';
  }

  return { parse, build };
})();
if (typeof module !== 'undefined') module.exports = X83;
