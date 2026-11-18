# Baut Gewerke-Anfragen.html aus app.html und den Bausteinen (alles in eine Datei, offline nutzbar).
# Ergebnis liegt im obersten Ordner des Projekts: ../../Gewerke-Anfragen.html
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = lambda f: open(os.path.join(HERE, f), encoding='utf-8').read()
a = src('app.html')
for k, f in [('/*DATA*/', 'data.js'), ('/*GAEB*/', 'gaeb.js'), ('/*X83*/', 'x83.js'), ('/*PDFJS*/', 'pdf.min.js'), ('/*PDFWORKER*/', 'pdf.worker.min.js'), ('/*PDFSITE*/', 'pdfsite.js'), ('/*ENGINE*/', 'engine.js'), ('/*KW*/', 'kw.json')]:
    a = a.replace(k, src(f))
out = os.path.normpath(os.path.join(HERE, '..', '..', 'Gewerke-Anfragen.html'))
open(out, 'w', encoding='utf-8').write(a)
print('gebaut:', out)
