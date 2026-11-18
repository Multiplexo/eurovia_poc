#!/usr/bin/env python3
"""Firmenadressen aus data.js über OpenStreetMap (Nominatim) auf Koordinaten umrechnen.

Ergebnis landet in geocache.json (Schlüssel "Straße|PLZ|Ort" -> [lat, lng] oder null).
Der Lauf ist fortsetzbar: bereits gesuchte Adressen werden übersprungen.
Nominatim erlaubt höchstens 1 Anfrage pro Sekunde.
Am Ende werden die Koordinaten direkt in data.js eingetragen (PLZ-Mittelpunkt bleibt, wo nichts gefunden wurde).
Danach build.py laufen lassen.
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'geocache.json')
UA = 'Gewerke-Anfragen-PoC/0.1 (einmalige Verortung einer Lieferantenliste)'

def key(f):
    return f"{f['str']}|{f['plz']}|{f['ort']}"

def search(params):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({**params, 'format': 'json', 'limit': 1, 'countrycodes': 'de'})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)
    return [round(float(j[0]['lat']), 5), round(float(j[0]['lon']), 5)] if j else None

def main():
    js = open(os.path.join(HERE, 'data.js'), encoding='utf-8').read()
    data = json.loads(js[js.index('{'):js.rindex('}') + 1])
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = [f for f in data['firms'] if f['str'] and key(f) not in cache]
    print(len(data['firms']), 'Firmen,', len(todo), 'noch zu suchen', file=sys.stderr)
    for i, f in enumerate(todo, 1):
        try:
            cache[key(f)] = search({'street': f['str'], 'postalcode': f['plz'], 'city': f['ort']})
        except Exception as e:
            print('Fehler', key(f), e, file=sys.stderr); time.sleep(5); continue
        if i % 25 == 0:
            json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
            print(i, 'von', len(todo), file=sys.stderr)
        time.sleep(1.1)
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    print('gefunden:', sum(1 for v in cache.values() if v), 'von', len(cache), file=sys.stderr)
    n = 0
    for f in data['firms']:
        ll = cache.get(key(f))
        if ll: f['geo'] = ll; n += 1
    open(os.path.join(HERE, 'data.js'), 'w', encoding='utf-8').write(js[:js.index('{')] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + js[js.rindex('}') + 1:])
    print(n, 'Firmen mit genauer Adresse in data.js', file=sys.stderr)

if __name__ == '__main__':
    main()
