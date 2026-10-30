# Changelog

## 1.3.3

- App-Store-Logo und -Icon ergänzt; Beschreibung überarbeitet.
- Wartungssperren-Entität und zugehörige Konfiguration entfernt.
- Sämtliche Zeiten fest auf `Europe/Berlin` mit automatischer Sommer-/Winterzeit umgestellt.
- Installationsgebundene Offline-Aktivierung mit RSA-Signatur ergänzt. Der private Signierschlüssel ist nicht Bestandteil der App oder öffentlichen ZIP.
- Dokumentation und Veröffentlichungsvorbereitung erweitert.

## 1.3.2

- Supervisor-Rolle auf `homeassistant` korrigiert.
- Eigene Supervisor-Verbindungsprüfung und eindeutige Meldungen für fehlenden, abgelehnten oder unzureichend berechtigten Token.
- Kompatibilität mit `HASSIO_TOKEN` und `X-Supervisor-Token` ergänzt.

## 1.3.1

- Home-Assistant-Prüfung startet automatisch mit jeder Wartung; manueller Prüfbutton entfernt.
- Eigener A4-Prüfbericht pro Prüfstand und neu gestaltete A4-Wartungsübergabe.
- Drei letzte Ereignisse direkt sichtbar; vollständige Ereignisliste über Augen-Symbol im Popup.
- Wartungsanzeige zeigt den Prüfstatus und die zurückgegebenen Ergebnisse.

## 1.3.0

- Termin-/Erinnerungsverwaltung und Statistik-/Ereignisreset.
- Fachkraft-Startdialog, drei Dauermodi, serverseitige Sperren und automatischer Abschluss.
- Lesende HA-Prüfberichte mit maximal drei Prüfständen und ausgewiesenen Zugriffsgrenzen.
- A4-PDF mit lokalem Logo, Standort, Fachkraft und Zeitangaben.
- Docker-Konfiguration, Dokumentation und Regressionstests aktualisiert.

## 1.2.2

- Wartungsfälligkeitsanzeige überarbeitet.

## 1.2.1

- Fehlende `build.yaml` ergänzt.
- Dockerfile auf architekturspezifisches `BUILD_FROM` umgestellt.
- Installations- und GitHub-Struktur dokumentiert.

## 1.2.0

- Fester, zufällig generierter Fachkraft-PIN beim ersten Start; nur gesalzener Hash persistent.
- PIN nicht mehr in der App-Konfiguration änderbar.
- GitHub-Repository-Metadaten aktualisiert.

## 1.1.0

- Installations- und Updateanleitung ergänzt.
- HTTP-Sicherheitsheader und begrenzte Sitzungslaufzeit ergänzt.

## 1.0.0

- Erste Version der Wartungsverwaltung.
