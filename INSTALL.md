# VantaNet Maintenance V1.3.0 - Installation

1. Vor einem Update ein Home-Assistant-App-Backup mit den persistenten `/data`-Daten erstellen. Die App für ein Update nicht deinstallieren.
2. ZIP entpacken. `repository.yaml` gehört in die Repository-Wurzel. Der vollständige App-Ordner heißt in diesem Quellarchiv `vantanet_maintenace` (bestehende Schreibweise erhalten).
3. Für ein lokales Add-on den Inhalt dieses App-Ordners in den bisherigen App-Ordner unter `/addons` übernehmen. Bei Neuinstallation z. B. `/addons/vantanet_maintenace/config.yaml`. Keine zusätzliche Verschachtelung anlegen. Bei einem Update den bereits verwendeten Ordnernamen beibehalten.
4. Lokale Apps im Home-Assistant-App-Store neu laden und VantaNet Maintenance installieren bzw. aktualisieren/neu erstellen. Version muss 1.3.0 sein. Alle Dateien inklusive `assets`, `maintenance_v130.py` und `reports.py` übernehmen.
5. Optionen für Tablet-IPs, Fully-Kiosk-Passwort, HA-URL, Dashboard-Pfad, öffentliche LAN-Adresse und Standort setzen. Beispiele in `config.yaml` durch eigene Werte ersetzen. Fully Kiosk benötigt Remote-Administration auf Port 2323. Container-Zeitzone prüfen.
6. App starten. Bei Erstinstallation den einmalig ausgegebenen 10-stelligen Fachkraft-PIN aus dem App-Protokoll sicher notieren. Bestehender PIN und Wartungszustand bleiben bei einem normalen Update erhalten.
7. Weboberfläche über Ingress öffnen. Startdialog, schnellen oder manuellen Testlauf, Tablet-Anzeige, SFRP und Abschluss prüfen. Zum Test keine produktive Wartung als technisch erfolgreich ausweisen.
8. Einen realen Prüfbericht anfordern. Je nach Rechten werden Systemwerte, Versionsstände, Geräte-/Entitätszahlen und Dateimetadaten geliefert oder ausdrücklich als nicht berechtigt/nicht verfügbar ausgewiesen. Danach A4-PDF prüfen.
9. 24-h-Erinnerung, Datumseinstellung, Deaktivieren und Löschen testen. Manuelle künftige Termine bleiben beim Abschluss erhalten.

Der App-Port 8765 muss von den Tablets im LAN erreichbar sein. Der interne Port ist 8099. Nicht ins Internet freigeben. Display-Token nicht weitergeben. Fehlende Tablet-Verbindung: IPs, Fully-Kiosk-Port, Passwort und `public_base_url` prüfen.

Die App verlangt die minimale Supervisor-Rolle `default`, Core-API-Zugriff und eine schreibgeschützte Home-Assistant-Konfigurationsfreigabe. Details in `vantanet_maintenace/DOCS.md`. Das Add-on führt keine echten Uploads, Löschungen, Updates oder Betriebssystem-Neustarts durch. Der Zeitablauf ist kein technischer Prüfnachweis.

Lokale Testabdeckung und verbleibende Inbetriebnahmeprüfungen stehen in `vantanet_maintenace/TEST_REPORT.md`. Ein echter HA-OS-Containerbuild und reale Tablet-/Supervisor-Verbindungen wurden in dieser Windows-Umgebung nicht ausgeführt.
