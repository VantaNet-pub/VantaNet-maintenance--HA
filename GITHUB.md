# Repository V1.3.0

`repository.yaml` bleibt im Hauptordner. Der App-Ordner `vantanet_maintenace` enthält `config.yaml`, `build.yaml`, `Dockerfile`, die drei Python-Module und `assets/logo.png`. Diese Struktur vollständig übernehmen. Der App-Slug bleibt `vantanet_maintenance`.

Nur Quellen, Logo, Dokumentation und Tests versionieren. Keine `/data`-Dateien, PIN-Hashes, Passwörter, Tokens, produktiven Prüfberichte oder Fachkraftdaten einchecken. Die ZIP enthält keine Laufzeitdaten.

Installation: `INSTALL.md`. Bedienung und Rechte: `vantanet_maintenace/DOCS.md`. Die Veröffentlichung oder ein Deployment wird durch dieses Paket nicht ausgeführt.
