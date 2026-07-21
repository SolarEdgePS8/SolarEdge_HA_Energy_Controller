# Changelog

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
