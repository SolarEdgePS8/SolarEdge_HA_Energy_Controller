# RC3 EVOpt Live-Nachweis vom 21.07.2026

## Ziel

Nachweis auf der Referenzinstallation, dass der RC3-Fix reguläre EVOpt-Slotwechsel nicht mehr fälschlich als inkonsistent bewertet und dadurch keinen unnötigen Fallback auf `Netzdienlich laden` auslöst.

## Testbedingungen

- Home Assistant Referenzinstallation mit SolarEdge-Speicher;
- Betriebsart `EVOpt optimiert`;
- Controller-Master `on`;
- EVOpt-Adapter `1.2.0`;
- Abfrageintervall 10 Sekunden;
- Test read-only, keine Helperänderung und kein direkter SolarEdge-Schreibbefehl durch den Test;
- beobachtete Aktion `holdcharge`;
- angeforderte und rückgemeldete Ladefreigabe `0 W / 0 W`.

## Beobachtete echte Slot-Fortschaltungen

### Slotwechsel um 17:00 Uhr

```text
vorher: slot_index=0, status=healthy, active_control=on
nachher: slot_index=1, status=healthy, active_control=on
action=holdcharge
soll/ist=0/0
```

Der Controller blieb während des regulären Viertelstundenwechsels durchgehend auf EVOpt. Es trat kein Fallback und kein zusätzlicher `0/5000-W`-Schreibzyklus auf.

### Slotwechsel um 17:30 Uhr

```text
17:30:42 status=healthy active=on slot=0 action=holdcharge soll/ist=0/0
17:30:52 status=healthy active=on slot=1 action=holdcharge soll/ist=0/0
17:31:02 status=healthy active=on slot=1 action=holdcharge soll/ist=0/0
```

Auch dieser echte Indexwechsel `0 → 1` blieb ohne Fallback. Status, aktive Steuerung, Aktion und Soll-/Istwert blieben konsistent.

## Solver-Replans korrekt abgegrenzt

Zwischen den regulären Slotwechseln erzeugte evcc neue Optimizer-Pläne. Dabei begann der neue Plan wieder mit `slot_index=0`, beispielsweise ungefähr um 17:02 und 17:33 Uhr. Diese Replans wurden nicht als Fehler gewertet und führten ebenfalls nicht zum Verlust der aktiven EVOpt-Steuerung.

## Gesamtergebnis

Über den beobachteten Zeitraum blieben die wiederholten Stichproben konsistent:

```text
sensor.se_nf_evopt_status = healthy
binary_sensor.se_nf_evopt_active_control = on
action = holdcharge
sensor.se_nf_desired_target = 0
sensor.se_nf_charge_limit_actual = 0
```

Es wurden bestätigt:

```text
REAL_SLOT_ADVANCES=2
EVOPT_STATUS_HEALTHY=PASS
EVOPT_ACTIVE_CONTROL=PASS
UNNECESSARY_FALLBACKS=0
UNNECESSARY_0_5000_WRITE_CYCLES=0
LIVE_TEST=PASS
```

## Aussagegrenze

Der Nachweis gilt für die konkrete Referenzinstallation und die beobachtete EVOpt-Aktion `holdcharge`. Die automatischen Vertrags- und Übergangstests decken zusätzlich die übrigen Aktionswechsel und die Unterscheidung zwischen restriktiven sofortigen sowie freizügigeren verzögerten Übergängen ab.
