# Modus: Akku schonen

## Ziel

Der Akku wird nur so weit und so früh geladen, wie es für den erwarteten Verbrauch, die Reserve und den nächsten Zeitraum sinnvoll ist.

## Benötigte Daten

- alle Pflichtdaten;
- Mindest- und Maximal-SoC;
- Nacht- und Tagesverbrauchsannahmen;
- Ziel- und Endzeit.

Optional:

- SQLite-Verbrauchshistorie;
- Wetter;
- PV-Prognose übermorgen;
- tatsächliche PV-Erträge.

## Fallback

Ohne gültige SQL-Historie verwendet der Modus die konfigurierten manuellen Verbrauchswerte. Die Funktion bleibt aktiv, arbeitet dann aber konservativer.

## Schutzmechanismen

- Zielgrenzen werden auf Plausibilität geprüft;
- Backup-Reserve wird berücksichtigt;
- Low-SoC- und Risikozustände können die normale Planung überstimmen;
- fehlende Pflichtdaten sperren den Writer.
