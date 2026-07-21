# Modus: Netzdienlich laden

## Ziel

Der Akku soll den prognostizierten PV-Überschuss aufnehmen, ohne unnötig früh oder dauerhaft mit maximaler Leistung zu laden.

## Benötigte Daten

- Akku-SoE und Kapazität;
- Rest-PV heute;
- PV-Prognose morgen;
- Live-PV-Leistung und Hausverbrauch;
- Zeitfenster und Ziel-SoC.

Optional verbessern Wetter, tatsächlicher PV-Ertrag und Verbrauchshistorie die Planung.

## Ablauf

1. Energiebedarf bis zum Ziel-SoC bestimmen.
2. verbleibende nutzbare PV-Energie bewerten.
3. spätesten sicheren Start berechnen.
4. Arbiter wählt die gültige Leistung.
5. Writer setzt nur bei relevanter Änderung und nach Ablauf des Write-Locks.

## Fallback

Fehlende optionale Daten werden konservativ ersetzt. Fehlende Pflichtdaten sperren den Writer.
