# Modus: Akku schonen

## Ziel

Der Speicher soll nicht unnötig früh oder unnötig hoch geladen werden. Das Ziel wird aus Verbrauch, Reserve, Akkustand und PV-Prognose abgeleitet.

## Benötigte Daten

Wie bei „Netzdienlich laden“:

- Akku-SoE und Kapazität;
- PV-Prognosen;
- Live-PV und Hausverbrauch.

## Besonders relevant

- Mindest- und Maximalziel;
- zusätzlicher Sicherheitspuffer;
- Nachtverbrauch;
- Tagesverbrauch;
- geplantes Ladefenster;
- Ziel-erreicht-Latch.

## SQL-Historie

Mit SQLite-Recorder kann der Controller:

- Restverbrauch des Tages aus bis zu sieben Vergleichstagen ableiten;
- Nachtverbrauch aus historischen Nachtfenstern bestimmen;
- Tagesverbrauch zwischen konfigurierten Zeitfenstern bestimmen.

Bei zu wenig Historie oder Datenbankfehlern werden konservative Fallbackwerte verwendet.

## Sicherheitsverhalten

Ein einmal erreichtes Ziel wird nicht durch eine fehlerhafte `done ↔ armed`-Schleife ständig neu geöffnet. Eine kontrollierte Latch-Korrektur greift nur bei plausiblen Bedingungen.
