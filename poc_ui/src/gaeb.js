// GAEB 90 (DA 83) lesen und Gewerke-Anfragen schreiben.
// Gleiche Logik wie gaeb_gewerke.py, damit UI und Script dieselben Dateien erzeugen.
const GAEB = (() => {
  // CP850, Bytes 0x80-0xFF
  const HI = 'ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜø£Ø×ƒáíóúñÑªº¿®¬½¼¡«»░▒▓│┤ÁÂÀ©╣║╗╝¢¥┐└┴┬├─┼ãÃ╚╔╩╦╠═╬¤ðÐÊËÈıÍÎÏ┘┌█▄¦Ì▀ÓßÔÒõÕµþÞÚÛÙýÝ¯´­±‗¾¶§÷¸°¨·¹³²■ ';
  const ENC = new Map([...HI].map((c, i) => [c, 0x80 + i]));

  function decode(bytes) {
    let s = '';
    for (const b of bytes) s += b < 0x80 ? String.fromCharCode(b) : HI[b - 0x80];
    return s;
  }
  function encode(str) {
    const out = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) {
      const c = str.charCodeAt(i);
      out[i] = c < 0x80 ? c : (ENC.get(str[i]) ?? 0x3F);
    }
    return out;
  }

  const rt = r => r.slice(0, 2);

  function readRecords(text) {
    let lines = text.replace(/\r\n/g, '\n').split('\n').filter(l => l.trim());
    // T0..T9-Block (z. B. Baubeschreibung) vor dem 00er-Satz wird nicht mit angefragt
    const start = lines.findIndex(l => rt(l) === '00');
    if (start > 0) lines = lines.slice(start);
    // 06er-Satz = Kostenarten der Kalkulation: 27er-Saetze und Kennzeichen in Spalte 19 sind intern
    if (lines.some(l => rt(l) === '06')) {
      lines = lines.filter(l => rt(l) !== '06' && rt(l) !== '27')
        .map(l => rt(l) === '21' ? l.slice(0, 18) + ' ' + l.slice(19) : l);
    }
    return lines;
  }

  function parse(text) {
    const recs = readRecords(text);
    const root = { open: [], children: [], close: null, title: '' };
    const stack = [root], header = [], items = [];
    let trailer = null, pending = [], cur = null;
    for (let i = 0; i < recs.length; i++) {
      const r = recs[i], t = rt(r);
      if (t === '99') trailer = r;
      else if (t === '11') {
        cur = null;
        const g = { open: [...pending, r], children: [], close: null, title: '', parent: stack[stack.length - 1] };
        pending = [];
        while (i + 1 < recs.length && rt(recs[i + 1]) === '12') {
          i++; g.open.push(recs[i]); g.title += recs[i].slice(2, 74).trim() + ' ';
        }
        g.title = g.title.trim();
        stack[stack.length - 1].children.push(g);
        stack.push(g);
      } else if (t === '31') {
        // 20er-Block direkt vor Gruppenende gehoert zu keiner Position
        cur = null; pending = [];
        stack[stack.length - 1].close = r;
        stack.pop();
      } else if (t === '20') { cur = null; pending.push(r); }
      else if (t === '21') {
        cur = { records: [...pending, r], oz: r.slice(2, 11), kurztext: '', langtext: '',
                menge: r.slice(23, 34), einheit: r.slice(34, 38).trim(), kat: r.slice(40, 72).replace(/\D/g, ''),
                group: stack[stack.length - 1] };
        pending = [];
        stack[stack.length - 1].children.push(cur);
        items.push(cur);
      } else if (cur) {
        cur.records.push(r);
        if (t === '25') cur.kurztext += r.slice(2, 74).trim() + ' ';
        if (t === '26') cur.langtext += r.slice(5, 74).trim() + ' ';
      } else if (pending.length) pending.push(r);
      else if (!root.children.length) header.push(r);
      else throw new Error(`Unerwarteter Satz ${t} in Zeile ${i + 1}`);
    }
    for (const it of items) {
      it.kurztext = it.kurztext.trim();
      it.langtext = it.langtext.trim();
      const m = parseInt(it.menge, 10);
      it.mengeNum = isNaN(m) ? 0 : m / 1000;
    }
    const field = t => (header.find(r => rt(r) === t) || '').slice(2, 74).trim();
    const h01 = header.find(r => rt(r) === '01') || '';
    const info = {
      lv: (header.find(r => rt(r) === '00') || '').slice(13, 30).trim(),
      bezeichnung: h01.slice(2, 42).trim(),
      name: field('02'), auftraggeber: field('03'),
    };
    return { header, root, trailer, items, info };
  }

  const pad = (s, n) => s.length >= n ? s : s + ' '.repeat(n - s.length);
  const num = (v, n) => String(v).padStart(n, '0');

  function emit(group, sel, out) {
    const body = [];
    for (const c of group.children) {
      if (c.records) { if (sel.has(c.oz)) body.push(...c.records); }
      else emit(c, sel, body);
    }
    if (!body.length) return out;
    out.push(...group.open, ...body);
    if (group.close) out.push(group.close);
    return out;
  }

  // Erzeugt den Text einer Gewerke-Anfrage. datum: 'TT.MM.JJ' oder null (aus LV)
  function build(lv, name, ozSet, datum) {
    const hdr = lv.header.map(r => {
      if (rt(r) === '02') return '02' + pad(name.slice(0, 72), 72) + r.slice(74);
      if (rt(r) === '01' && datum) return r.slice(0, 42) + datum + r.slice(50);
      return r;
    });
    const lines = [...hdr, ...emit(lv.root, ozSet, [])].map(r => r.slice(0, 74));
    const nPos = lines.filter(r => rt(r) === '21').length;
    const out = lines.map((r, i) => pad(r, 74) + num(i + 1, 6));
    if (lv.trailer !== null) out.push(pad(lv.trailer.slice(0, 69), 69) + num(nPos, 5) + num(out.length + 1, 6));
    return out.join('\r\n') + '\r\n';
  }

  // ------------------------------------------------ Gewerke-Vorschlag (Textaehnlichkeit)
  const tok = s => (s.toLowerCase().match(/[a-zäöüß0-9]+/g) || []).filter(w => w.length > 2);

  function makeSuggester(corpus) {
    // corpus: [[text, [codes]], ...]
    const df = new Map();
    corpus.forEach(([t]) => new Set(tok(t)).forEach(w => df.set(w, (df.get(w) || 0) + 1)));
    const N = corpus.length, idf = w => Math.log(N / (df.get(w) || 1));
    const vec = s => {
      const c = new Map();
      tok(s).forEach(w => c.set(w, (c.get(w) || 0) + 1));
      let n = 0; const v = new Map();
      c.forEach((k, w) => { const x = k * idf(w); v.set(w, x); n += x * x; });
      n = Math.sqrt(n) || 1; v.forEach((x, w) => v.set(w, x / n));
      return v;
    };
    const index = new Map(); // Wort -> [[docIdx, gewicht]]
    const labels = corpus.map(([, l]) => l);
    corpus.forEach(([t], d) => vec(t).forEach((x, w) => {
      if (!index.has(w)) index.set(w, []);
      index.get(w).push([d, x]);
    }));
    return function suggest(text) {
      const score = new Map();
      vec(text).forEach((x, w) => (index.get(w) || []).forEach(([d, y]) => score.set(d, (score.get(d) || 0) + x * y)));
      let best = -1, bs = 0;
      score.forEach((s, d) => { if (s > bs) { bs = s; best = d; } });
      return best < 0 ? { codes: [], score: 0 } : { codes: labels[best], score: bs };
    };
  }

  return { decode, encode, parse, build, makeSuggester, tok };
})();
if (typeof module !== 'undefined') module.exports = GAEB;
