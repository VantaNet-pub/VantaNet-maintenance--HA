# Prüfprotokoll V1.3.3

Stand: 30.10.2026. Grundlage: unveränderte Original-ZIP `VantaNet-maintenance--HA-main.zip`, lokal entpackt und bearbeitet. Testumgebung: Windows, Python 3.12.10. Alle folgenden Prüfungen beziehen sich auf den ausgelieferten Quellstand.

## Ergebnis

23 automatisierte Tests bestanden:

1. Start-/Hinweissperren während laufender Wartung und automatischer, einmaliger Abschluss.
2. PIN-Sitzungsanforderung und CSRF-Abweisung für geschützte Aktionen/PDF.
3. Darstellung des Startdialogs, drei sichtbare Ereignisse und vollständiges Ereignis-Popup.
4. Display-Token, automatischer Prüfstatus und lokal erreichbares Logo.
5. Manuelle Terminplanung, ungültige Termine und getrennte Resets.
6. Alle Dauermodi und Grenzwerte für manuelle Minuten.
7. Migration von V1.2-Zustand mit Erhaltung bestehender Zähler.
8. A4-Wartungsübergabe und eigener A4-Prüfbericht mit Fachkraft und Standort.
9. 24-h-Erinnerungszeit, erneute Anzeige, Deaktivieren/Löschen/Aktivieren.
10. Automatischer Prüfstart und höchstens drei gespeicherte Berichte nach fünf Wartungen.
11. Zufällige SFRP-Intervalle 15–20 Minuten; kein zusätzliches Verschieben durch Ende eines SFRP-Zyklus.
12. Persistenz von Timer und Fachkraftdaten beim erneuten Laden.
13. Geräte-Registry und Entitätszusammenfassung mit API-Testantworten.
14. Dateimetadaten ohne Übernahme von Dateiinhalten.
15. Ungültige Antworten und Zeitüberschreitungen.
16. Ausschluss von Testpasswörtern und Tokens aus Berichten.
17. 401/403, Serverfehler und fehlender Supervisor-Token.
18. Supervisor-Token über aktuellen und älteren Variablennamen sowie beide unterstützten HTTP-Header.
19. Deutsche Winterzeit UTC+1 und Sommerzeit UTC+2.
20. Nicht aktivierte Installationen werden auf die Aktivierungsseite umgeleitet.
21. Gültige RSA-Lizenz ist an exakt eine Installations-ID gebunden.
22. Manipulierte und abgelaufene Lizenzen werden abgewiesen.
23. Aktivierung wird ohne privaten Schlüssel unter `/data` gespeichert und erneut verifiziert.

Zusätzlich bestanden: Python-Syntaxprüfung aller Module, YAML-Einlesen, Übereinstimmung von Optionen/Schema und Build-Architekturen, erfolgreiche Auslieferung der Verwaltungs- und Displayseiten sowie JavaScript-Syntaxprüfung der gerenderten Skripte mit Node.js.

PDF: Wartungsübergabe und Prüfbericht wurden als A4-Dokumente erzeugt, mit PDFium gerendert und kontrolliert. Logo, Umlaute, Ränder, Seitenzahlen, Statusfelder und Unterschriftenbereiche sind lesbar. Die Beispiel-PDFs und sämtliche Test-Laufzeitdaten sind nicht Teil der ZIP.

## Reproduzieren

Im App-Ordner mit Python 3.12+: `python -m pip install -r requirements-dev.txt`, anschließend `python -m unittest -v test_app`.

## Nicht in dieser Umgebung durchgeführt

- Docker-/HA-OS-Imagebuild auf amd64, aarch64 oder armv7.
- Installation im Home-Assistant-Supervisor und echte API-/Registry-Abfragen.
- Bedienung von Fully-Kiosk-Tablets oder 24 Stunden dauernder Echtzeitbetrieb.
- Vollständiger Browser-End-to-End-Test.

API-Antworten, Berechtigungsfehler und Zeitabläufe wurden lokal mit kontrollierten Testdaten bzw. verstellter Testzeit geprüft. Nach Installation sind Build/Start, Zeitzone, API-Rechte, automatische Prüfberichte, Tablet-Umschaltung und beide PDF-Downloads zu prüfen. Details in `DOCS.md` und `../INSTALL.md`.

Das Paket enthält Quellen, statisches Logo, Dokumentation und Tests, aber keine Zugangsdaten, produktiven Daten oder lokale Testabhängigkeiten.
