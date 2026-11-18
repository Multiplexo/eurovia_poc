# Gewerke-Anfragen (PoC): Quellcode

> **Tool öffnen:** `Gewerke-Anfragen.html` in diesem Ordner per Doppelklick öffnen (Chrome oder Edge).
> `poc_ui/src/app.html` ist nur die Vorlage mit Platzhaltern und funktioniert allein nicht.

Proof of Concept für Eurovia: Aus einem Gesamt-LV (GAEB 90 `.D83` oder GAEB XML `.X83`) entsteht je Gewerk eine Anfrage-Datei für Subunternehmer, dazu eine Liste der nächstgelegenen passenden Anbieter aus der NU- und Lieferantenliste.

Das Ergebnis ist **eine einzige HTML-Datei** (`Gewerke-Anfragen.html`), die ohne Server und ohne Installation im Browser läuft, auch offline. Alle Daten bleiben im Browser.

## Schnellstart

Voraussetzung ist nur **Python 3** (ohne Zusatzpakete).

```bash
cd poc_ui/src
python3 build.py
```

Das erzeugt bzw. aktualisiert `Gewerke-Anfragen.html` im obersten Ordner. Diese Datei per Doppelklick in Chrome oder Edge öffnen. Zum Ausprobieren eine `.D83`-Datei hineinziehen und „Intelligente Zuordnung“ klicken.

**Wichtig:** `Gewerke-Anfragen.html` wird bei jedem Build überschrieben. Änderungen immer in den Quelldateien machen, nie in der gebauten HTML.

## Aufbau

```
Gewerke-Anfragen.html fertiges Tool (von build.py erzeugt, nicht von Hand ändern)
poc_ui/src/
  app.html            Vorlage: Oberfläche und Ablauf (5 Schritte, Reiter Subunternehmer/Regeln/Anleitung)
  engine.js           Gewerke-Vorschlag: Katalog-Regeln, Stichwörter, ähnlichste Position (TF-IDF)
  gaeb.js             GAEB 90 (DA 83) lesen und Gewerke-Dateien schreiben (CP850)
  x83.js              GAEB XML (X83) lesen und schreiben, gleiche Struktur wie gaeb.js
  pdfsite.js          liest die Baustelle aus der „Aufforderung zur Angebotsabgabe“ (PDF)
  pdf.min.js,
  pdf.worker.min.js   pdf.js (Fremdbibliothek, nicht ändern)
  kw.json             Start-Stichwortregeln (Wort -> Gewerk)
  data.js             erzeugte Daten: Beispiel-Positionen, Lieferanten, PLZ-Koordinaten, Gewerke
  build.py            setzt alles zu Gewerke-Anfragen.html zusammen
  prep.py             erzeugt data.js aus den Original-Daten (selten nötig, siehe unten)
  gewerke_def.py      Gewerke-Stammdaten: Kürzel, Name, Stichwörter für „Art der Arbeiten“, Umkreis km; ALIAS
  geocode_firms.py    verortet Firmenadressen über OpenStreetMap (optional)
  plz.csv             PLZ -> Koordinaten
gaeb_gewerke/
  gaeb_gewerke.py     Kommandozeile: Zuordnung aus Gewerke-Dateien auslesen / LV in Gewerke-Dateien zerlegen
  abgleich.py         vergleicht erzeugte mit echten Gewerke-Dateien (Qualitätsprüfung)
  abgleich_template.html  Ansicht für das Abgleich-Ergebnis
```

### Wie der Build funktioniert

`app.html` enthält Platzhalter wie `/*DATA*/`, `/*GAEB*/`, `/*ENGINE*/`. `build.py` ersetzt sie durch den Inhalt der jeweiligen Datei. Eine neue JS-Datei braucht also einen neuen Platzhalter in `app.html` und einen Eintrag in der Liste in `build.py`.

### Wie der Vorschlag funktioniert (`engine.js`)

Jede Position wird in dieser Reihenfolge geprüft:

1. **Katalog-Regel:** Die Katalognummer beginnt mit einem Präfix, das in den Beispielen eindeutig einem Gewerk zugeordnet ist (z. B. Straßen.NRW).
2. **Stichwort:** Ein Wort aus `kw.json` steht im Kurztext.
3. **Ähnlichste Position:** TF-IDF-Vergleich mit allen Beispiel-Positionen aus `data.js` und den im Browser gelernten Beispielen.

Regeln, Notizen, Sperren und gelernte Beispiele speichert die Oberfläche im `localStorage` des Browsers (Schlüssel beginnen mit `gwa.`).

## Daten neu erzeugen (optional)

Nur nötig, wenn sich die Beispiel-Ausschreibungen, die NU-Liste oder `gewerke_def.py` ändern. Braucht die Original-Daten (nicht in diesem Paket) und `openpyxl`:

```bash
pip install openpyxl
cd poc_ui/src
python3 prep.py "<Pfad>/Vergabepakete_Dateien" "<Pfad>/NU-und Lieferantenliste.xlsm"
python3 build.py
```

`prep.py` erwartet in `Vergabepakete_Dateien` je Paket einen Ordner (z. B. `K181_26_0272`) mit dem Gesamt-LV und den Gewerke-Dateien (`MARK_<LV>.D83` usw.). Die Zuordnung Paket -> Gesamt-LV steht in `MAIN` in `prep.py`.

Optional die Firmen genauer verorten (dauert wegen 1 Anfrage/Sekunde eine Weile, Ergebnis in `geocache.json`):

```bash
python3 geocode_firms.py
python3 build.py
```

## Qualitätsprüfung mit den Kommandozeilen-Werkzeugen

```bash
# Zuordnung aus vorhandenen Gewerke-Dateien auslesen
python3 gaeb_gewerke/gaeb_gewerke.py extract LV.D83 MARK_LV.D83 VS_LV.D83 -o zuordnung.json
# LV anhand der Zuordnung in Gewerke-Dateien zerlegen
python3 gaeb_gewerke/gaeb_gewerke.py split LV.D83 zuordnung.json -o anfragen/
# alle Pakete abgleichen: Ampel je Datei
python3 gaeb_gewerke/abgleich.py "<Pfad>/Vergabepakete_Dateien" ergebnis/data.json
```

Für die Ansicht in `abgleich_template.html` den Platzhalter `__DATA__` durch den Inhalt von `data.json` ersetzen.

## Hinweise

- `data.js` und damit die gebaute HTML enthalten die NU- und Lieferantenliste mit Kontaktdaten. Nur intern weitergeben.
- GAEB 90 ist in CP850 kodiert. `gaeb.js` und `gaeb_gewerke.py` müssen dieselben Dateien erzeugen. Bei Änderungen an der Logik beide anpassen.
- Firmen mit „nicht mehr anfragen“ in der Lieferantenliste haben eine vorbelegte Sperre bis 31.12.2025 (in `app.html`). Die ist inzwischen abgelaufen.
