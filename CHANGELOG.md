# Changelog

## Unreleased

- formales JSON-Schema für öffentliche 96-Slot-/15-Minuten-Fixtures ergänzt;
- Privacy-Scanner mit Selbsttest, GitHub-Annotations und Prüfung auf private Netze, Tokens, Gerätekennungen und nicht neutrale Home-Assistant-Entity-IDs ergänzt;
- lokaler Allowlist-Exporter für CSV-Tagesverläufe und Home-Assistant-State-Snapshots mit Rollenmapping ergänzt;
- zweites, ausdrücklich synthetisches und nur auf anonymisierte Tagesenergiesummen kalibriertes 24h-Fixture ergänzt;
- verpflichtende Home-Assistant-Smoke-Matrix auf 2026.7.3 und 2026.6.3 erweitert;
- nicht blockierenden täglichen Kompatibilitätstest gegen den aktuellen `stable`-Container ergänzt;
- standardisierte Failure-Bundles mit Workflow-Kontext, Dateiliste und SHA256-Prüfsummen ergänzt;
- versionierte Empfehlung für Branch-Protection und Pflichtchecks ergänzt;
- Codespaces-Dev-Container mit Python, Docker, ShellCheck, YAML- und GitHub-Actions-Unterstützung ergänzt;
- unabhängiges Python-Referenzmodell für Safety, alle vier Modi, EVOpt-Handover und Writer-Policy ergänzt;
- 29 feste synthetische Tag-/Nacht-/PV-/SoC-/Forecast-Szenarien sowie Hypothesis-, Grenzwert- und Fake-Time-Tests ergänzt;
- kontrollierbarer Fake-evcc-Server und Home-Assistant-2026.7.3-Container-Smoke-Test ergänzt;
- mehrstufiger GitHub-Actions-Workflow mit getrennten Artefakten und abschließendem Deep-Release-Gate ergänzt;
- keine Verbindung zu realer Hardware und keine Änderung an den 18 produktiven Package-YAMLs;
- Installer-Backups werden mit einem eindeutigen `mktemp`-Suffix erzeugt; mehrere Installations- oder Rollbacktests innerhalb derselben Sekunde können sich nicht mehr gegenseitig überschreiben;
- CI erzwingt denselben Zeitstempel für mehrere Installationsläufe und prüft die Kollisionssicherheit deterministisch;
- GitHub Actions auf Node-24-fähige Versionen aktualisiert: `checkout@v6`, `setup-python@v6` und `upload-artifact@v6`;
- Sensor- und Mapping-Dokumentation nach Herkunft, Bedeutung und Einheit erweitert: SolarEdge Modbus Multi, PV-Prognose, Wetter, evcc/ha-evcc sowie optionale Strompreis- und Kostenintegrationen;
- read-only Mapping-Assistent erkennt und bewertet Kandidaten, unterstützt OS/Supervised/Container/Core sowie Offline-State-Dateien und erzeugt nur eine unbestätigte `site_config.env`;
- Mapping-Assistent trägt LIVE-Leistung nur automatisch ein, wenn die Quelle bereits exakt `W` liefert; `kW`-Quellen bleiben als Konvertierungshinweis im Bericht;
- neutrale, optionale YAML-Beispiele für PV-Filter, Leistung-zu-Energie, Tageszähler, Forecast-, evcc- und Strompreisadapter ergänzt;
- Erstinstallation und Installer-Ausgabe um einen geführten Ablauf aus Installation, read-only Discovery, manueller Bestätigung, First Checks und später Master-Aktivierung ergänzt;
- keine Änderungen an den 18 produktiven Package-YAMLs oder an der Controller-Laufzeitlogik.

## v0.1.0-rc.4

- realen Startup-Zyklus `0 → 5000 → 0` analysiert und als Handover-Problem des einzigen Charge-Limit-Writers identifiziert;
- EVOpt-Startup-Handover hält im Modus `EVOpt optimiert` bei kurzen Ausfällen den zuletzt bestätigten SolarEdge-Zustand;
- vollständiger Fallback auf `Netzdienlich laden` erst nach 20 Minuten durchgehendem EVOpt-Ausfall;
- `holdcharge` wirkt restriktiv sofort und bleibt 180 Sekunden gelatcht;
- Freigabe auf `5000 W` erst nach 90 Sekunden stabilem finalem Sollwert und mit eigenem Nachtrigger;
- Writer-Trigger auf den bereits arbitrierten Sollwert und zentrale Freigaben reduziert;
- Tippfehler `sensor.se_nf_evopt_candidate_target` auf `sensor.se_nf_evopt_candidate_target_w` korrigiert;
- Master, Site-Konfigurationsbestätigung, EVOpt-Aktivierung und EVOpt-Basis-URL bleiben über Neustarts erhalten;
- Write-Watchdog `1.0.2` ergänzt: beobachtet `number.set_value`, Context-/Parent-Kette, Write-Intent, Zustandswechsel, doppelte Writes, Roundtrips, unerwartete Schreiber und EVOpt-Widersprüche;
- Watchdog-Fehlalarm behoben: rohe Aktion `holdcharge` ist nur bei aktiver EVOpt-Steuerung oder gelatchtem Charge-Block verbindlich;
- Installer installiert Watchdog und Terminal-Tools automatisch, ergänzt den Konfigurationsblock genau einmal und rollt alle Dateien sowie `configuration.yaml` bei Fehlern zurück;
- Runtime-Manifest von 23 auf 28 projektverwaltete Dateien erweitert;
- alle 18 Package-YAMLs per SHA256 byteidentisch zum geprüften Live-Export vom 22.07.2026 gemacht;
- CI um Live-Paritätsprüfung, RC4-Vertragstests, Watchdog-Syntax sowie Installations- und Rollbacksimulation erweitert;
- Erstinstallation, Update, EVOpt-Handover, Watchdog, Troubleshooting und technischer Status vollständig dokumentiert;
- Referenzinstallation: `19 OK, 0 Fehler`, EVOpt `healthy`, Soll/Ist `0/0 W`, Watchdog `ok` und nach Neustart keine neuen Schreib- oder Mismatch-Ereignisse.

## v0.1.0-rc.3

- falsche EVOpt-Fallbacks an regulären 15-Minuten-Slotwechseln behoben;
- `suggestion.action` wird nur verwendet, solange sie zum aktuellen Planabschnitt passt;
- in Folgeslots wird die Aktion aus dem vollständig validierten aktuellen Slot abgeleitet;
- neue EVOpt-Diagnosen für Suggestion, Slot-Aktion, Override-Grund und Plankonsistenz;
- restriktive EVOpt-Übergänge wirken unmittelbar, freizügigere Übergänge werden stabilisiert;
- Fallbackcode, Startzeit und Dauer präzisiert;
- Runtime-Checker, Installer, Release-Build und Release-Manifest einheitlich auf `0.1.0-rc.3` gesetzt;
- Release-Manifest um den exakten GitHub-Quellcommit ergänzt;
- Installer-Rollback auf Fehler im gesamten Installationsablauf erweitert;
- Erstinstallation und Update mit exakten Kommandos, Prüfsummen, erwarteten Zuständen und Rollback neu dokumentiert;
- EVOpt-Basis-URL, API-Prüfung, Warm-up und Health-Attribute eindeutig beschrieben;
- GitHub Actions erzeugt und prüft das finale ZIP und veröffentlicht nach erfolgreichem Merge dasselbe getestete Bundle als Prerelease;
- Referenzinstallation mit `ha core check`, Runtime-Manifest und SHA256 aller 23 Projektdateien geprüft;
- reale EVOpt-Planabschnittswechsel ohne Ausfall der aktiven Steuerung und ohne unnötigen Fallback beobachtet.

## v0.1.0-rc.2

- eigenständiges Repository vom älteren Projekt `Solaredge_Netzdienlich` getrennt;
- 18 portable Controller-Pakete;
