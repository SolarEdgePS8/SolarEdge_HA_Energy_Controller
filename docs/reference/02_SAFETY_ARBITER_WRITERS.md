# Safety, Arbiter und Writer

## Safety

Prüft Site-Konfiguration, Pflichtentitäten, Datenalter, Wertebereiche und Zielgrenzen. Ein ungültiger Zustand erzeugt keinen normalen Schreibauftrag.

## Arbiter

Erhält die Anforderungen der vier Modi und wählt genau eine gültige Zielanforderung. Sicherheits- und Prioritätszustände dürfen die normale Modusplanung überstimmen.

## Writer

Jedes Ziel besitzt genau einen Controller-Writer:

- Charge-Limit;
- Discharge-Limit;
- Storage Control;
- Command Mode.

Die zentrale Schreibfreigabe verlangt Master, bestätigte Site-Konfiguration sowie Config und Sanity jeweils `ok`. Die Writer prüfen zusätzlich ihre Ziel-Mappings, Werte, Sperrzeiten und modusspezifischen Bedingungen.

Leere optionale Mappings bedeuten: Der Controller besitzt dieses Ziel nicht und schreibt es nicht.
