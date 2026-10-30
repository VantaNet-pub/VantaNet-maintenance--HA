# Prüfprotokoll V1.3.0

Stand: 30.10.2026. Grundlage: unveränderte Original-ZIP `VantaNet-maintenance--HA-main.zip`, lokal entpackt und bearbeitet. Testumgebung: Windows, Python 3.12.10. Alle folgenden Prüfungen beziehen sich auf den ausgelieferten Quellstand.

## Ergebnis

17 automatisierte Tests bestanden:

1. Start-/Hinweissperren während laufender Wartung und automatischer, einmaliger Abschluss.
2. PIN-Sitzungsanforderung und CSRF-Abweisung für geschützte Aktionen/PDF.
3. Darstellung des Startdialogs und höchstens drei sichtbare Ereignisse.
4. Display-Token, Kennzeichnung als Simulation, lokal erreichbares Logo.
5. Manuelle Terminplanung, ungültige Termine und getrennte Resets.
6. Alle Dauermodi und Grenzwerte für manuelle Minuten.
7. Migration von V1.2-Zustand mit Erhaltung bestehender Zähler.
8. PDF-Abruf, A4-Seitenformat, Fachkraft/Standort und Simulationshinweis.
9. 24-h-Erinnerungszeit, erneute Anzeige, Deaktivieren/Löschen/Aktivieren.
10. Höchstens drei gespeicherte Berichte nach fünf Prüfläufen.
11. Zufällige SFRP-Intervalle 15–20 Minuten; kein zusätzliches Verschieben durch Ende der visuellen Sequenz.
12. Persistenz von Timer und Fachkraftdaten beim erneuten Laden.
13. Geräte-Registry und Entitätszusammenfassung mit API-Testantworten.
14. Dateimetadaten ohne Übernahme von Dateiinhalten.
15. Ungültige Antworten und Zeitüberschreitungen.
16. Ausschluss von Testpasswörtern und Tokens aus Berichten.
17. 401/403, Serverfehler und fehlender Supervisor-Token.

Zusätzlich bestanden: Python-Syntaxprüfung aller Module, YAML-Einlesen, Übereinstimmung von Optionen/Schema und Build-Architekturen, erfolgreiche Auslieferung der Verwaltungs- und Displayseiten sowie JavaScript-Syntaxprüfung der gerenderten Skripte mit Node.js.

PDF: Zwei A4-Seiten mit Beispiel-Fachkraft und nicht verfügbarem Supervisor wurden erzeugt, mit PDFium gerendert und visuell kontrolliert. Logo, Umlaute, Ränder, Seitenzahlen und Unterschriftenfelder lesbar; Prüfüberschriften und Ergebnisse werden zusammengehalten. Die Beispiel-PDF und sämtliche Test-Laufzeitdaten sind nicht Teil der ZIP.

## Reproduzieren

Im App-Ordner mit Python 3.12+: `python -m pip install -r requirements-dev.txt`, anschließend `python -m unittest -v test_app`.

## Nicht in dieser Umgebung durchgeführt

- Docker-/HA-OS-Imagebuild auf amd64, aarch64 oder armv7.
- Installation im Home-Assistant-Supervisor und echte API-/Registry-Abfragen.
- Bedienung realer Fully-Kiosk-Tablets oder 24 Stunden dauernder Echtzeitbetrieb.
- Vollständiger visueller Browser-End-to-End-Test.

API-Antworten, Berechtigungsfehler und Zeitabläufe wurden lokal mit kontrollierten Testdaten bzw. verstellter Testzeit geprüft. Das ist ausdrücklich kein Nachweis einer erfolgreichen Prüfung der tatsächlichen Anlage. Nach Installation: Build/Start, Zeitzone, API-Rechte, reale Prüfberichte, Tablet-Umschaltung und PDF-Download prüfen. Details in `DOCS.md` und `../INSTALL.md`.

Das Paket enthält Quellen, statisches Logo, Dokumentation und Tests, aber keine Zugangsdaten, produktiven Daten oder lokale Testabhängigkeiten.
