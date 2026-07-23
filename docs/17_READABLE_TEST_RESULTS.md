# Verständliche Testergebnisse

Die GitHub-Tests erzeugen zusätzlich zu technischen Logs einen Bericht in normaler Sprache.

## Wo ist der Bericht zu sehen?

1. Im Repository **Actions** öffnen.
2. Den Lauf **Deep SolarEdge Controller Testbench** öffnen.
3. In der Übersichtsseite des Laufs erscheint der Abschnitt **Verständlicher Testbericht**.
4. Zusätzlich liegt unter **Artifacts** im Paket `real-day-24h-<Commit>` die Datei:

```text
TEST_RESULT_READABLE.md
```

## Was steht darin?

Der Bericht beantwortet unter anderem:

- Wurden alle vier Betriebsarten vollständig getestet?
- Wie viele simulierte Stunden und 15-Minuten-Entscheidungen wurden geprüft?
- Wie viele echte Schreibbefehle hat der produktive Single Writer ausgelöst?
- Gab es einen nicht erlaubten Schreiber?
- Gab es ein unerwünschtes `0 ↔ 5000 W`-Flattern?
- Welche Sollwerte wurden je Betriebsart beobachtet?
- Welcher konkrete Steuerungsfehler wurde gefunden?
- Welche bekannten Grenzen hat der Test?

## Beispiel eines grünen 24h-Laufs

Der aktuelle Referenztest erwartet:

| Betriebsart | simulierte Dauer | Entscheidungen | erwartete Schreibbefehle |
|---|---:|---:|---:|
| Eigenverbrauch maximieren | 24 h | 96 | 1 × `5000 W` |
| Netzdienlich laden | 24 h | 96 | 0, wenn das Register bereits auf `0 W` steht |
| Akku schonen | 24 h | 96 | 0, wenn das Register bereits auf `0 W` steht |
| EVOpt optimiert | 24 h | 96 | `5000 W` und anschließend `0 W` |

Zusammen sind das:

```text
4 Betriebsarten
96 simulierte Stunden
384 Entscheidungen
3 echte Schreibbefehle
0 nicht erlaubte Schreiber
0 harte Steuerungsfehler
0 unerwünschte 0↔5000-W-Roundtrips
```

## Wichtige Grenze: „Akku voll oder nicht voll“

Der 24h-Replay spielt einen anonymisierten Messverlauf mit PV-Leistung, Hausverbrauch und Ladestand ein. Der Test berechnet den Batterie-Ladestand derzeit nicht selbst aus den Writer-Befehlen.

Deshalb kann der Bericht zuverlässig sagen:

- ob die Steuerlogik korrekt geöffnet oder geschlossen hat;
- wie oft geschrieben wurde;
- ob unnötig hin- und hergeschaltet wurde;
- ob Safety, Mapping und Single-Writer-Regel eingehalten wurden.

Er kann noch nicht beweisen:

- ob eine reale Batterie am Tagesende voll wäre;
- wie viele kWh die jeweilige Betriebsart real geladen hätte;
- wie sich Wirkungsgrad, Modbus-Latenz und Wechselrichter-Firmware auswirken.

Dafür ist künftig ein geschlossenes Batteriemodell erforderlich, das den SoC für jeden Modus separat aus PV, Verbrauch, Ladefreigabe, Leistungslimit und Wirkungsgrad fortschreibt.

## Fehlerdarstellung

Bei einem roten Ergebnis nennt der Bericht den Fehler verständlich, zum Beispiel:

```text
❌ EVOpt verlangte Ladesperre, das Lade-Limit war aber offen
   Betriebsart: EVOpt optimiert
   Zeitpunkt: 04:15
```

Die vollständigen JSON-, Event- und Home-Assistant-Logs bleiben weiterhin erhalten, falls eine technische Ursachenanalyse nötig ist.
