# Changelog

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
- vier Betriebsarten mit zentraler Safety- und Arbiter-Logik;
- neutrale optionale externe Schnittstellen;
- dynamische Mappings für Charge-Limit, Discharge-Limit, Command Mode und Storage Control;
- EVOpt-Adapter mit vollständigem Fallback auf „Netzdienlich laden“;
- Installer, Migration, Update, Rollback, Runtime-Manifest und Konfliktprüfung;
- lokale Fahrzeug-, Wallbox-, Wärmepumpen-, Shelly-, Preis- und Akku-Saver-Abhängigkeiten entfernt;
- Referenzmigration, Aktivierung und realer Writer-Rundlauf verifiziert;
- MIT-Lizenz und vollständige Einsteiger-Dokumentation ergänzt.
