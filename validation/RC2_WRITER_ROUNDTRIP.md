# RC2 Writer-Rundlauf – bestanden

## Ergebnis

Der reale Charge-Writer-Rundlauf auf der Referenzinstallation wurde am 21.07.2026 erfolgreich abgeschlossen.

1. Ausgangszustand: Modus `EVOpt optimiert`, Soll 0 W, Ist 0 W.
2. Controller-Master ausgeschaltet und Writer-Sperre bestätigt.
3. Modus `Eigenverbrauch maximieren` bei gesperrtem Writer vorbereitet.
4. Controller-Master eingeschaltet.
5. Echter SolarEdge-Write von 0 W auf 5000 W bestätigt.
6. Ursprünglichen Modus `EVOpt optimiert` wiederhergestellt.
7. Echter SolarEdge-Write von 5000 W auf 0 W bestätigt.
8. Ursprünglicher Masterzustand `AN` wiederhergestellt.

## Release-Gates

```text
OPEN_WRITE=PASS
CLOSE_WRITE=PASS
WRITER_ROUNDTRIP=PASS
```

## Beobachtete Zustände

```text
OPEN_WRITE:
  target=5000 W
  actual=0 W -> 5000 W
  writer=priority_open -> idle

CLOSE_WRITE:
  target=0 W
  actual=5000 W -> 0 W
  writer=blocked_lock -> idle
```

Der kurze Zustand `blocked_lock` beim Schließen war ein erwarteter Übergang. Innerhalb von drei Sekunden wurde das reale Charge-Limit korrekt auf 0 W zurückgesetzt.

## Wiederhergestellter Abschlusszustand

```text
Modus: EVOpt optimiert
Master: AN
Charge-Limit: 0 W
Config Check: ok
Sanity Check: ok
Risk Flag: off
```

Damit ist der reale Charge-Writerwechsel für `v0.1.0-rc.2` verifiziert.
