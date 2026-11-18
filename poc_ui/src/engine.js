// Gewerke-Vorschlag: Katalog-Regeln, Stichwort-Regeln, aehnliche Positionen.
const ENGINE = (() => {
  // Leistungsbereich-Schluessel aus der Katalognummer (die ersten 3 Ziffern sind die Katalogausgabe)
  const katKey = kat => (kat && kat.length > 6 ? kat.slice(3) : '');

  // Katalog-Regeln aus Beispielen ableiten: Praefix -> Gewerke, wenn eindeutig genug
  function learnKatRules(examples, { minN = 5, purity = 0.75 } = {}) {
    const rules = [];
    for (const len of [3, 5]) {
      const g = new Map();
      for (const e of examples) {
        const k = katKey(e.kat); if (k.length < len) continue;
        const p = k.slice(0, len);
        if (!g.has(p)) g.set(p, []);
        g.get(p).push(e.codes.slice().sort().join('+'));
      }
      for (const [p, v] of g) {
        if (v.length < minN) continue;
        const c = new Map(); v.forEach(x => c.set(x, (c.get(x) || 0) + 1));
        const [best, n] = [...c].sort((a, b) => b[1] - a[1])[0];
        if (n / v.length < purity) continue;
        // feinere Regel nur, wenn sie etwas anderes sagt als die grobe
        const coarse = rules.find(r => p.startsWith(r.prefix));
        if (coarse && coarse.codes.join('+') === best) continue;
        rules.push({ prefix: p, codes: best ? best.split('+') : [], n: v.length, quote: Math.round(100 * n / v.length) });
      }
    }
    return rules.sort((a, b) => b.prefix.length - a.prefix.length);
  }

  const tok = s => (s.toLowerCase().match(/[a-zäöüß0-9]+/g) || []).filter(w => w.length > 2);

  function makeKnn(examples) {
    const df = new Map();
    examples.forEach(e => new Set(tok(e.text)).forEach(w => df.set(w, (df.get(w) || 0) + 1)));
    const N = examples.length || 1, idf = w => Math.log(N / (df.get(w) || 1));
    const vec = s => {
      const c = new Map(); tok(s).forEach(w => c.set(w, (c.get(w) || 0) + 1));
      let n = 0; const v = new Map();
      c.forEach((k, w) => { const x = k * idf(w); v.set(w, x); n += x * x; });
      n = Math.sqrt(n) || 1; v.forEach((x, w) => v.set(w, x / n)); return v;
    };
    const index = new Map();
    examples.forEach((e, d) => vec(e.text).forEach((x, w) => { if (!index.has(w)) index.set(w, []); index.get(w).push([d, x]); }));
    return text => {
      const score = new Map();
      vec(text).forEach((x, w) => (index.get(w) || []).forEach(([d, y]) => score.set(d, (score.get(d) || 0) + x * y)));
      let best = -1, bs = 0; score.forEach((s, d) => { if (s > bs) { bs = s; best = d; } });
      return best < 0 ? null : { ex: examples[best], score: bs };
    };
  }

  // kw-Regeln: [{wort, codes}] ; kat-Regeln: [{prefix, codes}]
  function make(examples, kwRules, katRules) {
    const knn = makeKnn(examples);
    const kws = kwRules.map(r => ({ ...r, re: new RegExp(r.wort.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') }));
    return function suggest(pos) {
      // 1. Katalognummer
      const k = katKey(pos.kat);
      if (k) {
        const r = katRules.find(r => k.startsWith(r.prefix));
        if (r) return { codes: r.codes.slice(), reason: `Katalog-Regel ${r.prefix}`, why: `die Katalognummer mit ${r.prefix} beginnt (Katalog-Regel)`, sure: true };
      }
      // 2. Stichwörter im Kurztext
      const hits = kws.filter(r => r.re.test(pos.kurztext));
      if (hits.length) {
        const codes = [...new Set(hits.flatMap(r => r.codes))];
        return { codes, reason: 'Stichwort ' + hits.map(r => '„' + r.wort + '“').join(', '), why: 'der Kurztext ' + hits.map(r => '„' + r.wort + '“').join(', ') + ' enthält (Stichwort-Regel)', sure: true };
      }
      // 3. ähnlichste bekannte Position
      const m = knn(pos.kurztext + ' ' + (pos.langtext || '').slice(0, 200));
      if (!m) return { codes: [], reason: 'keine ähnliche Position bekannt', sure: false };
      return { codes: m.ex.codes.slice(), reason: `ähnlich wie „${m.ex.kurz}“ (${m.ex.src})`, sure: m.score >= 0.35, score: m.score, ex: m.ex };
    };
  }

  return { make, learnKatRules, katKey };
})();
if (typeof module !== 'undefined') module.exports = ENGINE;
