# VantaNet Maintenance 1.2.0 – INSTALLATION

Stand: 29.10.2026. Ziel: Home Assistant OS auf Raspberry Pi (aarch64).

## 1. Vorher sichern

Erstelle in Home Assistant unter **Einstellungen → System → Backups** ein Backup. Sichere außerdem `/addons/vantanet_maintenance/` und, falls die App bereits lief, deren persistente `/data`-Daten über ein Home-Assistant-App-Backup. Die App speichert ihren Wartungszustand in `/data/maintenance.json`.

## 2. ZIP auf den Home-Assistant-Server kopieren

Die ZIP-Datei kannst du über Studio Code Server in einen Ordner unter `/homeassistant/` hochladen, z. B. `/homeassistant/vantanet-maintenance/`. Die Befehle unten im **Studio Code Server Terminal** ausführen, nicht im offiziellen Terminal-&-SSH-Container, dessen `/addons` ein anderer Ordner sein kann.

Wenn du dieses ZIP nach `/homeassistant/vantanet-maintenance/VantaNet_Maintenance_1.2.0.zip` hochgeladen hast:

```sh
mkdir -p /addons/vantanet_maintenance
unzip -o /homeassistant/vantanet-maintenance/VantaNet_Maintenance_1.2.0.zip 'vantanet_maintenance/*' -d /addons/
ha store reload
ha apps info local_vantanet_maintenance
```

**Wichtig:** Der Pfad muss `/addons/vantanet_maintenance/config.yaml` sein. Keine zusätzliche Ebene `/addons/local/` anlegen. `ha store reload` ist der relevante Befehl zur Aktualisierung der App-Store-Erkennung.

## 3. App installieren oder aktualisieren

Home Assistant → **Einstellungen → Apps → App-Store → Lokale Apps → VantaNet Maintenance**. Bei Neuinstallation auf **Installieren** klicken. Bei bestehender Installation prüfen, ob **Update** angeboten wird. Falls kein Update angeboten wird, in der App **Neu erstellen / Rebuild** wählen, nachdem die neue `config.yaml` auf dem Datenträger liegt. **Nicht deinstallieren**, wenn du bestehende Daten behalten willst.

Der erste Build lädt ggf. das Basisimage und Alpine-Pakete aus dem Internet. Das kann dauern. Build und Start wurden nicht auf deinem Gerät getestet.

## 4. Konfiguration

In der App unter **Konfiguration**:

- **Fachkraft-PIN:** Beim ersten Start wird automatisch ein fester 10-stelliger PIN erzeugt. Er erscheint **nur einmal** in den App-Protokollen. Sofort sicher notieren! Danach liegt ausschließlich ein gesalzener PBKDF2-Hash unter `/data/technician_pin.json`; keine Änderung über die App-Konfiguration möglich. Bei Verlust ist eine gezielte Wiederherstellung erforderlich; die PIN-Datei nicht leichtfertig löschen.
- `kiosk_password`: das aktuelle Fully-Kiosk-Remote-Admin-Passwort beider Tablets (vorher das im Chat geteilte Passwort ändern).
- `tablet_ips`: `192.168.4.60`, `192.168.4.61`.
- `home_assistant_url`: `http://192.168.4.2:8123`.
- `dashboard_path`: `/home-db/0?hide_sidebar` (das `?` ist wichtig).
- `public_base_url`: `http://192.168.4.2:8765`.
- `first_maintenance_due`: optional Datum nach ISO-Format, z. B. `2026-11-01T09:00:00+01:00`. Leer bedeutet beim erstmaligen Start sofort fällig.

Einstellungen speichern, **Beim Booten starten** und **Watchdog** nach Bedarf aktivieren, App starten. In den Logs auf Startfehler prüfen. Die App verwendet intern Port 8099 und stellt den Display-Port über 8765 bereit.

## 5. App aufrufen und testen

In Home Assistant → Apps → VantaNet Maintenance → **Weboberfläche öffnen**. Einmaligen Fachkraft-PIN aus dem ersten Startprotokoll sicher notieren und eingeben. Dann:

1. **Wartung starten**: beide Tablets auf den Upload-Bildschirm setzen.
2. **SFRP**: visuelle Shutdown/Update/Startup-Sequenz auslösen.
3. **Wartung abschließen**: Tablets zum Dashboard zurückführen, nächste Fälligkeit auf sechs Kalendermonate nach Abschluss setzen.
4. **Wartungshinweis anzeigen**: Hinweis manuell testen. Der Button **Okay** blendet ihn für 24 Stunden aus.

Die Upload-Dauer wird beim Start zufällig auf 40–120 Minuten gesetzt. Alle 15 Minuten läuft eine visuelle Neustartsequenz. Der Wartungsabschluss geschieht **nur** über die Verwaltungsoberfläche, nicht durch das Erreichen von 100 %.

## 6. Bedienung und Statistik

Die PIN-geschützte Oberfläche bietet Start, Abschluss, Wartungshinweis, SFRP, Status, Restzeit, nächsten Termin, Start-/Abschlusszahlen, Erinnerungsbestätigungen und Ereignisse. Die bisherigen `vn mt ...`-Konsolenbefehle sind für die App-Bedienung nicht mehr erforderlich.

## 7. Fernzugriff über Nabu Casa

Öffne die App über die Home-Assistant-Seitenleiste bzw. ihre Ingress-Weboberfläche, nicht über `https://...ui.nabu.casa:8765`. Port 8765 ist für den lokalen Displayzugriff gedacht und sollte **nicht** per Router-Portfreigabe öffentlich gemacht werden. PIN-Schutz ersetzt keine sichere Home-Assistant-Anmeldung.

## 8. GitHub-Updates

Der ZIP-Inhalt ist bereits als Home-Assistant-App-Repository strukturiert (`repository.yaml` + `vantanet_maintenance/`). Du kannst ihn auf GitHub hochladen. **Privat** funktioniert das Repository aber nicht ohne Weiteres als direkte Home-Assistant-App-Store-Quelle: Der Supervisor muss es authentifiziert klonen können. Einfach eine private GitHub-URL einzutragen reicht nicht.

Empfehlung: Privat auf GitHub versionieren und Releases manuell in den lokalen `/addons`-Ordner übernehmen (über Studio Code Server, wie in Schritt 2). Alternativ kann später ein abgesicherter automatischer Deployment-Prozess mit einem eingeschränkten Deploy-Key eingerichtet werden. Niemals PIN, Kiosk-Passwort oder Tokens ins Repository committen.

## 9. Fehlerbehebung

- App fehlt: `ha store reload` und `ha apps info local_vantanet_maintenance`.
- `does not exist`: Pfad `/addons/vantanet_maintenance/config.yaml` prüfen, `ha supervisor logs` ansehen.
- Build schlägt fehl: App-Protokoll/Build-Log prüfen; Internetzugang und Paketdownload kontrollieren.
- PIN funktioniert nicht: PIN aus dem ersten Startprotokoll prüfen. Der PIN wird bei weiteren Starts nicht erneut ausgegeben.
- Tablets reagieren nicht: IPs, Port 2323, Fully-Kiosk-Remote-Admin und Netzwerkzugriff prüfen.
- Display zeigt nichts: Tablet-Browser muss `http://192.168.4.2:8765` erreichen können.
- Nach Neustart fehlt Python im Terminal: Die App bringt Python selbst mit; `apk add python3` im Terminal ist nicht nötig.

## Sicherheit und technische Grenzen

Diese Version wurde lokal auf Syntax und Paketstruktur geprüft, aber **nicht auf deinem Home-Assistant-Raspberry-Pi installiert oder im echten Betrieb getestet**. Die PIN ist ein zweiter Schutz innerhalb der bereits authentifizierten Home-Assistant-Oberfläche. Der App-Statusdienst und die Display-URLs sind über lokale Zugriffstokens erreichbar; diese URLs nicht weitergeben. Der Zugang über Ingress hängt zusätzlich von der Home-Assistant-Anmeldung ab. Ein produktiver Einsatz sollte erst nach erfolgreichem Tablet-Test und Backup erfolgen.

Der Upload-Screen zeigt bewusst erfundene Dateioperationen; er führt keine Uploads, Löschungen, Backups oder Betriebssystem-Neustarts aus. Die visuelle Darstellung darf nicht als Nachweis einer tatsächlich ausgeführten Wartung verstanden werden.

## Öffentliches GitHub-Repository

Dieses Repository ist öffentlich. **Keine** privaten IPs, PINs, Zugangsdaten, Tokens oder produktiven Konfigurationsdateien hochladen. Die IP-Adressen in `config.yaml` sind derzeit Beispielwerte aus einer konkreten Umgebung und sollten vor Wiederverwendung geprüft werden.
