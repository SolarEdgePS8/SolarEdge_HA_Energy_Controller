# Modus: Eigenverbrauch maximieren

## Ziel

Der Speicher arbeitet möglichst normal für den eigenen Haushalt. Der Controller hält das Charge-Limit geöffnet, solange keine Sicherheitsbedingung entgegensteht.

## Benötigte Daten

Pflicht:

- Charge-Limit;
- Akku-SoE;
- Akkukapazität;
- bestätigte Site-Konfiguration;
- gültiger Config- und Sanity-Check.

Nicht benötigt:

- Wetter;
- SQL-Historie;
- evcc;
- EVOpt;
- externe Preis- oder Fahrzeugsignale.

## Verhalten

Der Modus erzeugt grundsätzlich den offenen Charge-Limit-Wert. Safety und Arbiter können die Anforderung sperren.

Typischer Session-State: `open`.

Bei ungültiger Konfiguration oder Risiko: `risk`.

Bei ausgeschaltetem Master: `closed`.

## Fallbacks

Dieser Modus ist der einfachste unabhängige Funktionstest. Optionale Datenquellen dürfen fehlen, ohne den Modus zu blockieren.

## Prüfen

- Modus auswählen;
- Master einschalten;
- `sensor.se_controller_self_consumption_charge_target_w` prüfen;
- `sensor.se_nf_desired_target` vergleichen;
- tatsächliches Charge-Limit beobachten.
