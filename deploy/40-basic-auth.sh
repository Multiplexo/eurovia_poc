#!/bin/sh
# Erzeugt /etc/nginx/.htpasswd aus BASIC_AUTH_USER / BASIC_AUTH_PASSWORD.
# Ohne Passwort startet der Container bewusst nicht (Daten enthalten Kontaktdaten).
set -e
if [ -z "$BASIC_AUTH_PASSWORD" ]; then
  echo "FEHLER: Umgebungsvariable BASIC_AUTH_PASSWORD ist nicht gesetzt. Container startet nicht ohne Passwortschutz." >&2
  exit 1
fi
USER="${BASIC_AUTH_USER:-eurovia}"
printf '%s:%s\n' "$USER" "$(printf '%s' "$BASIC_AUTH_PASSWORD" | cryptpw -m sha512)" > /etc/nginx/.htpasswd
chmod 644 /etc/nginx/.htpasswd
echo "Basic Auth aktiv für Benutzer: $USER"
