# RC2 – realer Writer-Rundlauf

Der reale Charge-Writer wurde auf der Referenzinstallation geprüft:

```text
OPEN_WRITE=PASS
CLOSE_WRITE=PASS
WRITER_ROUNDTRIP=PASS
```

Ablauf:

1. Baseline: EVOpt, Master an, Charge-Limit 0 W.
2. Master aus und Writer gesperrt.
3. Modus „Eigenverbrauch maximieren“ vorbereitet.
4. Master an: Charge-Limit real auf 5000 W gesetzt.
5. Ursprünglichen EVOpt-Modus wiederhergestellt.
6. Charge-Limit real auf 0 W zurückgesetzt.
7. Masterzustand an und Ausgangsmodus wiederhergestellt.

Runtime-Manifest, Pflichtentitäten, Mappings, Config und Sanity waren gültig. Der Runtime-Checker meldete `PASS=True`.
