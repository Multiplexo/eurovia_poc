# Gewerke-Anfragen: statische Single-File-App hinter nginx mit Passwortschutz.
# Stufe 1: HTML aus den Quellen bauen
FROM python:3.12-alpine AS build
WORKDIR /app
COPY poc_ui/src ./poc_ui/src
RUN cd poc_ui/src && python3 build.py

# Stufe 2: ausliefern
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/40-basic-auth.sh /docker-entrypoint.d/40-basic-auth.sh
RUN chmod +x /docker-entrypoint.d/40-basic-auth.sh
COPY --from=build /app/Gewerke-Anfragen.html /usr/share/nginx/html/index.html
EXPOSE 80
