## 1.2.2
- Wartungfällig Anzeige verändert

## 1.2.1
- Fehlende build.yaml ergänzt.
- Dockerfile auf architekturspezifisches BUILD_FROM umgestellt.
- Installations- und GitHub-Struktur dokumentiert.

## 1.2.0
- Fester, zufällig generierter Fachkraft-PIN beim ersten Start; nur gesalzener Hash persistent.
- PIN nicht mehr in der App-Konfiguration änderbar.
- GitHub-Repository-Metadaten aktualisiert.

# Changelog

## 1.1.0 – 29.10.2026
- Installations- und Updateanleitung ergänzt.
- Gültige Schema-Typen `str` statt `password`.
- Docker-Basisimage explizit festgelegt; keine veraltete BUILD_FROM-Abhängigkeit.
- JavaScript-Protokollausgabe korrigiert.
- Zusätzliche HTTP-Sicherheitsheader und begrenzte Sitzungslaufzeit.
- GitHub-Vorbereitung und Installationsprüfungen.

## 1.0.0
- Erste Version der Wartungsverwaltung.
# V1.3.1

- Home-Assistant-Prüfung startet automatisch mit jeder Wartung; manueller Prüfbutton entfernt.
- Eigener A4-Prüfbericht pro Prüfstand und vollständig neu gestaltete A4-Wartungsübergabe.
- Drei letzte Ereignisse direkt sichtbar; vollständige Ereignisliste über Augen-Symbol im Popup.
- Wartungsanzeige zeigt ausschließlich den tatsächlichen Prüfstatus und die zurückgegebenen Ergebnisse.
- Optionale Wartungssperre schaltet eine konfigurierte Home-Assistant-Entität beim Start ein und beim Abschluss aus.

# V1.3.0

- Termin-/Erinnerungsverwaltung und Statistik-/Ereignisreset.
- Fachkraft-Startdialog, drei Dauermodi, serverseitige Sperren, automatischer Abschluss.
- Lesende HA-Prüfberichte mit maximal drei Prüfständen und ausgewiesenen Zugriffsgrenzen.
- A4-PDF mit lokalem Logo, Standort, Fachkraft und Zeitangaben.
- Docker-Konfiguration, Dokumentation und Regressionstests aktualisiert.

