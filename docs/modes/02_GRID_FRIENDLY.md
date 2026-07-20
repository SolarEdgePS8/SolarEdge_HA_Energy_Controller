# Modus: Netzdienlich laden

## Ziel

Der Speicher wird nicht sofort vollständig für das Laden geöffnet. Der Controller plant ein Zeitfenster, damit erwartete PV-Energie besser genutzt und unnötige Lade- oder Einspeisespitzen reduziert werden.

## Benötigte Daten

- Charge-Limit;
- Akku-SoE;
- Akkukapazität;
- PV-Prognose heute verbleibend;
- PV-Prognose heute gesamt;
- PV-Prognose morgen;
- aktuelle PV-Leistung;
- aktueller Hausverbrauch.

## Optional

- Wetter;
- SQL-Verbrauchshistorie;
- Prognose übermorgen;
- tatsächlicher PV-Ertrag;
- Tagesverbrauch;
- aktuelle PV-Leistungsprognose.

## Verhalten

Der Modus berechnet:

- benötigte Energie bis zum Ziel;
- verbleibende nutzbare PV-Energie;
- erwarteten restlichen Hausverbrauch;
- frühesten sinnvollen Start;
- späteste Fertigstellung;
- Session-State `armed`, `open`, `done` oder einen Sicherheitszustand.

## Fallbacks

Ohne Wetter wird mit neutralen oder konservativen Faktoren geplant.

Ohne SQL-Historie greift der eingestellte Tagesverbrauchs- und Nachtbedarfs-Fallback.

Dieser Modus ist zugleich der vollständige Fallback für EVOpt.
