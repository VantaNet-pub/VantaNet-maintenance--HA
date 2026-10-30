# VantaNet Maintenance V1.3.1

Home-Assistant-App für halbjährliche Wartungsanzeigen, PIN-geschützte Bedienung, Tablet-Steuerung, Fortschrittsanzeige und Ereignisstatistik.

Neu: Statistiken/Ereignisse zurücksetzen, Termin manuell setzen, 24-h-Erinnerung anzeigen/löschen/deaktivieren, Startdialog mit Fachkraft und Standort, Dauermodi automatisch 80–120 / schnell 20–60 / manuell 1–1440 Minuten und automatische Fertigstellung. Die Home-Assistant-Prüfung startet mit jeder Wartung automatisch und erstellt einen eigenen A4-Prüfbericht. Die letzten drei Ereignisse erscheinen direkt; das Augen-Symbol öffnet die vollständige Ereignisliste. SFRP bleibt zufällig alle 15–20 Minuten erhalten.

Optional kann `maintenance_lock_entity` auf eine Entität wie `switch.wartungsmodus` gesetzt werden. Die App aktiviert sie beim Start und deaktiviert sie beim Abschluss der Wartung.

Installationsanleitung: `INSTALL.md` im Paket.
