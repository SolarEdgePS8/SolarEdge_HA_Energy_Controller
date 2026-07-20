# Migration von einem älteren Controllerprojekt

Die Migration übernimmt nur den Controller. Andere lokale Automationen bleiben bestehen.

## Ablauf

1. Alten Master ausschalten.
2. Vollständiges Backup erstellen.
3. Neues Release entpacken.
4. Migration starten:

   ```bash
   bash scripts/migrate_existing.sh
   ```

5. Home Assistant neu starten.
6. Mapping und Runtime-Prüfung kontrollieren.
7. Externe Writer-Konflikte beheben.
8. Erst danach den neuen Master aktivieren.

## Was nicht automatisch geschieht

- Fremde Automationen werden nicht gelöscht.
- `.storage` wird nicht kopiert.
- Private Tokens oder Passwörter werden nicht übernommen.
- Command-Mode und Storage-Control werden nicht automatisch aktiviert.
- Schreibkonflikte werden gemeldet, aber nicht automatisch behoben.

## Koexistenz mit alten Automationen

Für jedes SolarEdge-Ziel muss ein Eigentümer festgelegt werden.

Beispiel:

- Controller besitzt Charge-Limit;
- vorhandene lokale Automation besitzt Backup-Reserve;
- Command-Mode bleibt ungemappt;
- externe EV-Automation setzt nur einen neutralen Request-Sensor.

Direkte parallele Schreibzugriffe auf dasselbe Ziel sind nicht zulässig.
