# Vorbereitung einer öffentlichen Veröffentlichung

V1.3.4 ist technisch für eine spätere Veröffentlichung strukturiert, wird durch dieses Paket aber nicht veröffentlicht.

Vor einem öffentlichen Release:

1. Eine passende rechtliche Lizenz und Nutzungsbedingungen festlegen. Ein sichtbarer Quellcode mit Aktivierung ist „source available“ und nicht automatisch Open Source.
2. Sicherstellen, dass `private_key.pem`, Signierwerkzeug, ausgestellte Lizenzen, `/data`, PIN-Dateien, Optionen, Prüfberichte und Kundendaten nie im Repository oder Release liegen.
3. Multi-Architektur-Builds für `amd64`, `aarch64` und das weiterhin konfigurierte `armv7` auf Home Assistant OS testen.
4. Installation, Update, Backup/Wiederherstellung, Ingress, Tablet-Steuerung, Supervisor-Zugriff, Zeitzonenwechsel und Aktivierung auf einer Testanlage prüfen.
5. Datenschutzinformationen für Fachkraft-, Standort- und Berichtsdaten veröffentlichen.
6. Supportweg, Sicherheitskontakt, Versionsstrategie und Verfahren bei Verlust oder Offenlegung des privaten Signierschlüssels festlegen.
7. Repository-URL, Maintainerangaben, Screenshots und Release-Notizen finalisieren.

Die lokale RSA-Signatur verhindert, dass reguläre Nutzer selbst Lizenzen erzeugen. Da der Prüfcode öffentlich einsehbar wäre, kann sie eine bewusste Quellcodeänderung nicht technisch ausschließen. Ein Online-Lizenzdienst könnte stärkere Durchsetzung, Sperrlisten und Gerätewechsel ermöglichen, benötigt aber Serverbetrieb, Datenschutzkonzept und Ausfallstrategie.
