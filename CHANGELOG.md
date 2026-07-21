# Changelog

## 0.1.0-rc.2 – vorbereitet

Erster portabler Release Candidate des eigenständigen SolarEdge HA Energy Controllers.

### Enthalten

- vier Betriebsarten: Eigenverbrauch, Netzdienlich, Akku schonen und EVOpt;
- neutraler Entity-Mapping-Layer für unterschiedliche Home-Assistant-Installationen;
- zentrale Safety- und Arbiter-Logik;
- eindeutige Writer für Charge-Limit, Discharge-Limit, Storage Control und Command Mode;
- EVOpt-Adapter mit sicherem Fallback auf netzdienliche Planung;
- optionale Wetter- und SQL-/Recorder-Prognosen mit Fallbackwerten;
- Installer, Migration, Update, Rollback und Runtime-Checker;
- verständliche Installations-, Mapping-, Modus- und Integrationsdokumentation;
- GitHub-Actions-Prüfungen und Modusvertragstests.

### Verifiziert

- statisches Release-Gate: PASS;
- kontrollierte Live-Migration: PASS;
- aktive Überwachung mit 60 Messungen: PASS;
- realer Charge-Writer-Rundlauf 0 W → 5000 W → 0 W: PASS;
- Ausgangsmodus `EVOpt optimiert`, Master `AN` und Charge-Limit `0 W` wiederhergestellt.

### Sicherheit

- fremde Fahrzeug-, Wallbox-, Wärmepumpen-, Preis- und Reserve-Automationen sind nicht Teil des Projekts;
- lokale URLs und private Entity-Abhängigkeiten wurden entfernt;
- Site-Konfiguration und Writer bleiben bis zur bestätigten Einrichtung gesperrt;
- Command Mode und Storage Control können ungemappt bleiben.

### Veröffentlichung

Der Stand ist für ein öffentliches Prerelease vorbereitet. Vor Merge und Release ist noch eine ausdrückliche Lizenzentscheidung erforderlich.
