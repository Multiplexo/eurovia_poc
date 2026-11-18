# Hinweise für Claude

Projektbeschreibung, Aufbau und Befehle stehen in README.md. Bitte zuerst lesen.

- Antworte auf Deutsch.
- Niemals `Gewerke-Anfragen.html` (oberster Ordner) bearbeiten. Sie wird von `build.py` erzeugt. Änderungen gehören in `app.html`, `engine.js`, `gaeb.js`, `x83.js`, `pdfsite.js`, `kw.json` oder `gewerke_def.py`.
- `data.js` (1,6 MB, eine Zeile) und `pdf*.min.js` nicht komplett einlesen und nicht von Hand ändern. `data.js` entsteht durch `prep.py`. Für die Struktur reicht der Anfang: `const DATA={corpus, firms, plz, orte, arten, gewerke, alias}`.
- Nach jeder Änderung `cd poc_ui/src && python3 build.py` ausführen und die HTML im Browser mit einer echten `.D83` testen.
- Die Oberfläche muss als einzelne Datei offline laufen: keine externen Skripte, kein Server, kein Build-Tool außer `build.py`.
- `gaeb.js` und `gaeb_gewerke/gaeb_gewerke.py` implementieren dieselbe GAEB-90-Logik (CP850). Änderungen an einer Seite auch auf der anderen nachziehen.
- Dateinamen mit Umlauten (SCHÜTT, BÜRO) kommen auf dem Mac zerlegt (NFD) an. In Python mit `unicodedata.normalize('NFC', …)` vergleichen.
