Siehe `INSTALL.md` im ZIP für die vollständige Einrichtung. Die Oberfläche ist PIN-geschützt; die Display-URLs verwenden ein separates Zugriffstoken.
# Betrieb und Berechtigungen V1.3.1

## Installation / Aktualisierung

Den vollständigen Ordner `vantanet_maintenace` unverändert in ein Home-Assistant-Add-on-Repository oder das lokale `/addons` übernehmen. Die bestehende Schreibweise des Ordnernamens bleibt erhalten. App neu bauen und starten. Vorher `/data` sichern. Vorhandene Statistiken, Termine, Ereignisse und PIN-Hash bleiben erhalten; neue Felder werden ergänzt.

`config.yaml` verwendet `homeassistant_api: true`, `hassio_api: true`, die minimale Supervisor-Rolle `default` sowie `homeassistant_config:ro`. Einzelne Systemabfragen können deshalb nicht erlaubt sein; der Bericht zeigt dies an. Die Freigabe `/homeassistant` wird nur für Metadaten von `configuration.yaml`, `automations.yaml`, `scripts.yaml` und `scenes.yaml` genutzt. Kein Dateiinhaltszugriff, kein rekursiver Scan, keine `.storage`- oder `secrets.yaml`-Auswertung.

## Optionen

- `site_location`: Vorbelegung für den Standort im Startdialog.
- `maintenance_lock_entity`: Optionale Entität für die Wartungssperre, z. B. `switch.wartungsmodus`. Sie wird beim Wartungsstart über `homeassistant.turn_on` aktiviert und beim manuellen oder automatischen Abschluss über `homeassistant.turn_off` deaktiviert. Bleibt das Feld leer, ist die Funktion ausgeschaltet. Der Schaltstatus wird in den Ereignissen protokolliert.
- `kiosk_password`: Fully-Kiosk-Passwort; nicht in Prüfberichten ausgegeben.
- `tablet_ips`: Fully-Kiosk-Geräte mit aktivierter Remote-Administration (Port 2323).
- `home_assistant_url`, `dashboard_path`: Dashboard nach Bestätigung oder Abschluss.
- `public_base_url`: Von den Tablets erreichbare Adresse dieser App, z. B. `http://192.168.1.2:8765`. Nicht die Ingress-Adresse.
- `first_maintenance_due`: ISO-Datum für die Erstinitialisierung, optional mit UTC-Offset. Wirkt nicht rückwirkend auf vorhandenen Zustand.

Formulartermine beziehen sich auf die lokale Zeitzone des App-Containers. Diese in Home Assistant korrekt einstellen. Das PDF nennt die Zeitzone beim Wartungsbeginn. 24 Stunden sind exakt 86.400 Sekunden, auch über eine Zeitumstellung hinweg.

## Erinnerung und Wartung

„Okay · in 24 Stunden erinnern“ gibt den nächsten Zeitpunkt zurück und öffnet das Dashboard. Nach Ablauf wird der Hinweis erneut auf den Tablets geöffnet. „Löschen“ entfernt die vorgemerkte 24-h-Erinnerung und deaktiviert die Erinnerung; „Deaktivieren“ pausiert sie und behält den Zeitpunkt. Beide schließen einen angezeigten Hinweis. „Aktivieren“ oder ein neuer Termin aktiviert sie wieder. Der nächste Wartungstermin bleibt beim Löschen erhalten. Ein bereits überfälliger aktivierter Termin erscheint beim nächsten Takt.

Neue Wartungen aktivieren nach Abschluss die Erinnerung. Zukünftige manuell gesetzte Wartungstermine bleiben beim Abschluss erhalten; sonst folgt der Termin sechs Kalendermonate nach Abschluss. Start und Hinweis sind während der Wartung im Browser und serverseitig gesperrt. Der automatische Abschluss erfolgt beim nächsten 5-Sekunden-Takt, nach einem App-Neustart auch rückwirkend für einen verstrichenen Timer. Wiederholtes Abschließen erhöht keine Statistik. Statistiken zurücksetzen verändert keinen laufenden Timer.

SFRP läuft während einer Wartung zufällig alle 15–20 Minuten; ein manueller SFRP-Start plant das nächste Intervall neu. Die drei neuesten Ereignisse erscheinen direkt in der Verwaltung. Das Augen-Symbol öffnet alle gespeicherten Ereignisse in einem Popup; intern werden maximal 100 Einträge behalten.

## Automatische Prüfberichte

Mit dem Start einer Wartung beginnt automatisch ein Hintergrundlauf. Währenddessen kann keine zweite Wartung gestartet werden. Nur die letzten drei fertigen Berichte werden in `/data/maintenance.json` gespeichert. Jeder Check enthält Zeitpunkt des Prüfstands, Quelle, Status und eine Zusammenfassung. Jeder Prüfstand kann als eigener A4-Prüfbericht heruntergeladen werden.

| Bereich | Quelle | Aussage und Grenze |
| --- | --- | --- |
| System / Core | GET `/core/info` | Installierte und angebotene Version |
| Ressourcen | GET `/core/stats` | CPU/Arbeitsspeicher, soweit Rolle dies erlaubt |
| Updates | GET `/supervisor/info`, `/os/info` | Versionsvergleich laut API, kein aktives Erneuern des Updatekatalogs |
| Geräte / Entitäten | GET `/core/api/states` | Anzahl, nicht verfügbare/unbekannte Zustände, aktive Update-Entitäten |
| Geräte / Registry | WS `/core/websocket`, `config/device_registry/list` | Registrierte und deaktivierte Geräte; kein physischer Funktionstest |
| Dateien | Read-only-Freigabe | Größe und Änderungszeit der vier erlaubten Dateien, kein Inhalts- oder Integritätstest |

401/403 bedeutet „nicht berechtigt“; fehlender Token, fehlende Dateien, Verbindungsfehler oder ungültige Antworten bedeuten „nicht verfügbar“. Geräte- und Entitätsnamen, Rohantworten, Passwörter, Tokens und Dateiinhalte werden nicht gespeichert. Zugang ausschließlich über den Supervisor-Laufzeit-Token; Fehler werden ohne rohe Netzwerkantworten gespeichert.

Offizielle Referenzen (abgeglichen am 30.10.2026):
https://contributors.home-assistant.io/apps/supervisor-api/
https://contributors.home-assistant.io/apps/supervisor-api/core/

## PDF und Datenschutz

Nach dem ersten Abschluss steht die neu gestaltete A4-Wartungsübergabe zur Verfügung. Sie enthält ausschließlich den Prüfbericht, der über die Wartungs-ID mit dieser Wartung verknüpft ist. Zusätzlich besitzt jeder gespeicherte Prüfstand einen eigenen A4-Download. Fachkraft und Standort werden lokal gespeichert; dort keine Zugangsdaten eingeben. Das mitgelieferte Logo erfordert keinen Internetabruf.

PIN und CSRF schützen Änderungen und PDF-Abruf. Display-URLs verwenden ein separates Token. Der PIN wird beim ersten Start einmalig im App-Protokoll angezeigt; danach liegt nur sein gesalzener Hash in `/data`. App-Port nicht ins Internet freigeben. Datenordner und Backups passend schützen.

## Entwicklung und Tests

Python 3.12+: `python -m pip install -r requirements-dev.txt`, dann im App-Ordner `python -m unittest -v test_app`. Tests nutzen einen temporären Datenordner. `VANTANET_DATA` ermöglicht lokale App-Daten, `VANTANET_CONFIG` eine Test-Konfigurationsfreigabe, `VANTANET_TEST_PDF` optional eine Beispiel-PDF-Ausgabe. Im produktiven Container nicht erforderlich.

Supervisor-, Geräte- und Tablet-Verbindungen müssen nach Installation an der Anlage geprüft werden. Die lokalen Tests ersetzen diese Inbetriebnahme nicht.
