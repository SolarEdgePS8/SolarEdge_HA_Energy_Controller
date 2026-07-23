# EVOpt-Nachtflattern: Live-Nachweis und Korrektur

## Beobachteter Fehler

Auf der Referenzinstallation wechselte das SolarEdge Storage Charge Limit nachts wiederholt zwischen `0 W` und `5000 W`.

Der Write-Watchdog belegte:

- alle echten Schreibbefehle kamen vom erlaubten zentralen Charge-Limit-Writer;
- es gab keinen zweiten konkurrierenden Writer;
- der finale Sollwert wechselte tatsächlich;
- kurze permissive EVOpt-Phasen waren lang genug, um die vorhandene 90-Sekunden-Freigabe zu passieren;
- anschließend setzte `holdcharge` das Limit wieder sofort auf `0 W`.

Damit lag die Ursache nicht im Writer, sondern in einer zu kurzen Freigabeentprellung des EVOpt-Charge-Blocks.

## Lokal geprüfte Korrektur

`holdcharge` bleibt weiterhin sofort restriktiv. Die Aufhebung des Charge-Blocks erfolgt erst nach 20 Minuten durchgehend stabiler Gegenentscheidung:

```yaml
delay_off:
  seconds: 1200
```

Die bestehende 90-Sekunden-Stabilisierung des finalen Writer-Sollwerts bleibt zusätzlich erhalten. Eine Ladefreigabe benötigt damit praktisch mindestens rund 21,5 Minuten stabilen permissiven Zustand.

## Live-Ergebnis

```text
TEST_BEGINN=2026-07-23T11:00:01+02:00
POST_FIX_WRITE_CALLS=0
```

Die Auswertung wurde wiederholt. Seit Testbeginn wurde kein echter `number.set_value`-Aufruf auf das SolarEdge-Charge-Limit registriert.

## Sicherheitswirkung

- `holdcharge → 0 W` bleibt sofort wirksam;
- kurze `normal`-Impulse öffnen das Charge-Limit nicht mehr;
- der Single-Writer-Grundsatz bleibt unverändert;
- es wird kein zusätzlicher SolarEdge-Schreibpfad eingeführt;
- bei dauerhaft permissiver EVOpt-Planung bleibt eine Freigabe möglich.

## Testgrenze

Der Live-Nachweis bestätigt das Ausbleiben der zuvor beobachteten Schreibzyklen im geprüften Zeitraum. Er beweist nicht das Verhalten jeder SolarEdge-Firmware oder jeder fremden Home-Assistant-Installation. Der Write-Watchdog bleibt deshalb nach Installation aktiv und der Stand bleibt ein Release Candidate.
