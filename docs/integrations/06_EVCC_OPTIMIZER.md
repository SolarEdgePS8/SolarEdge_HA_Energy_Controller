# evcc Optimizer / EVOpt

## Architektur

Der Python-Adapter liest den Optimizer-Plan über die evcc-API. Er schreibt nicht direkt auf SolarEdge.

Die Daten werden als interne Status- und Anforderungssensoren bereitgestellt. Der Arbiter entscheidet anschließend zusammen mit Safety über die tatsächliche Steuerung.

## Einrichtung

1. evcc und Optimizer einrichten.
2. API-Erreichbarkeit prüfen.
3. Basis-URL lokal eintragen.
4. Batterietitel oder Batteriename angeben.
5. `EVOPT_ENABLED=YES` setzen.
6. Site-Konfiguration anwenden.
7. Runtime-Status prüfen.
8. Erst danach den Modus `EVOpt optimiert` wählen.

## Fehlerfälle

- API nicht erreichbar;
- falsche Batterie;
- unbekanntes Schema;
- Plan veraltet;
- Plan außerhalb des Zeitfensters;
- widersprüchliche Strategie;
- Adapterstatus nicht `ok`.

In allen Fällen wird der EVOpt-Plan verworfen und `Netzdienlich laden` verwendet.
