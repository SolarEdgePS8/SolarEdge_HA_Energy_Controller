# RC2 Writer-Rundlauf – letzter Live-Test

## Ziel

Ein realer, kontrollierter Charge-Writer-Rundlauf auf der Referenzinstallation:

1. Ausgangszustand prüfen: Soll 0 W, Ist 0 W, Config/Sanity ok, Risk off.
2. Controller-Master ausschalten und Writer-Sperre bestätigen.
3. Modus `Eigenverbrauch maximieren` bei gesperrtem Writer vorbereiten.
4. Master einschalten und den echten Controller-Write auf 5000 W bestätigen.
5. Ursprünglichen Modus wiederherstellen.
6. Den echten Controller-Write zurück auf 0 W bestätigen.
7. Ursprünglichen Masterzustand wiederherstellen.

## Sicherheitsverhalten

Bei jeder Abweichung:

- ursprüngliches Charge-Limit direkt wiederherstellen;
- ursprünglichen Modus wiederherstellen;
- Controller-Master ausschalten;
- Fehlerbericht unter `/share` schreiben.

## Vorprüfung

Der Test startet nur, wenn:

- `sensor.se_nf_config_check = ok`;
- `sensor.se_nf_sanity_check = ok`;
- `binary_sensor.se_nf_risk_flag = off`;
- Charge-Soll und Charge-Ist jeweils höchstens 50 W sind;
- das Charge-Limit auf eine vorhandene `number.*`-Entity gemappt ist.

## Ausführbare Datei

`finalize_controller_rc2.py`

SHA256:

```text
c46a4abe520d552d6eda889a99b5310245c6a67462be0738128d35da44a8a5a1
```

## Freigabekriterium

```text
OPEN_WRITE=PASS
CLOSE_WRITE=PASS
WRITER_ROUNDTRIP=PASS
```

Erst danach gilt der reale Charge-Writerwechsel als verifiziert.