// Baustelle aus der „Aufforderung zur Angebotsabgabe“ (PDF) lesen. pdf.js ist eingebettet, die Seite bleibt offline nutzbar.
const PDFSITE = (() => {
  let ready = null;
  function init() {
    if (!ready) {
      const src = document.getElementById('pdfworker').textContent;
      pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([src], { type: 'text/javascript' }));
      ready = Promise.resolve();
    }
    return ready;
  }
  // Text der ersten Seiten, Zeilen wie im PDF
  async function text(file, pages = 3) {
    await init();
    const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    let out = '';
    for (let i = 1; i <= Math.min(pages, pdf.numPages); i++) {
      const page = await pdf.getPage(i);
      const c = await page.getTextContent();
      out += c.items.map(t => t.str + (t.hasEOL ? '\n' : '')).join('') + '\n';
      // ausgefüllte Formularfelder (z. B. Baumaßnahme im Vordruck 211) stehen nicht im Seitentext
      const ann = await page.getAnnotations();
      out += ann.map(a => typeof a.fieldValue === 'string' ? a.fieldValue : '').filter(Boolean).join('\n') + '\n';
    }
    return out;
  }
  const STR = /([A-ZÄÖÜ][a-zäöüß-]+(?:er)? (?:Straße|Str\.|Weg|Allee|Ring|Platz|Damm|Chaussee)|[A-ZÄÖÜ][a-zäöüß-]+(?:straße|str\.|weg|allee|ring|platz|damm|chaussee))(?![a-zäöüß])/g;
  const ORT = '([A-ZÄÖÜ][a-zäöüß-]+(?: [A-ZÄÖÜ][a-zäöüß-]+)?)';
  // ort: Ort aus dem LV (z. B. „Stadt Bielefeld“), falls die Aufforderung keinen nennt
  function site(t, ort) {
    // 1. ausdrückliche Angabe „Baustelle“ in der nächsten Zeile, z. B. „Detmolder Straße, 33607 Bielefeld“
    const b = /(?:^|\n)\s*(?:Baustelle|Ort der Ausführung|Ausführungsort)\s*:?\s*\n?\s*([^\n]+\d{5}[^\n]*)/i.exec(t);
    if (b) return b[1].trim();
    // 2. erste Straße ohne Hausnummer (Hausnummer = Anschrift des Auftraggebers),
    //    zuerst hinter „Baumaßnahme“ o. Ä., dann im ganzen Text
    const k = /Baumaßnahme|Bauvorhaben|Bezeichnung der Bauleistung/.exec(t);
    for (const part of [k ? t.slice(k.index, k.index + 600) : '', t]) {
      for (const m of part.matchAll(STR)) {
        const after = part.slice(m.index + m[0].length, m.index + m[0].length + 8);
        if (/^\s*\d/.test(after) || /vergabe|markt/i.test(m[1])) continue;
        const s = m[1].replace(/Str\.$/, 'Straße');
        return ort ? `${s}, ${ort}` : s;
      }
    }
    // 3. Landes-/Bundesstraße: „OD Marsberg“, „zw. Ochtrup und Gronau“, „L 755 Bad Driburg“
    const road = /\b([ABLK] \d{1,4})\b/.exec(t);
    const town = new RegExp('\\b(?:OD|zw\\.|zwischen)\\s+' + ORT).exec(t) || new RegExp('\\b[ABLK] \\d{1,4} ' + ORT).exec(t);
    if (town) return [road && road[1], town[1]].filter(Boolean).join(', ');
    return '';
  }
  return { text, site };
})();
