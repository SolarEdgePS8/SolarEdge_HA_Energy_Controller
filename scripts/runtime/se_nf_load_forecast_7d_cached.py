#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path
import time
import sys

DEFAULT_DB = Path("/config/home-assistant_v2.db")
BAD = {"", "unknown", "unavailable", "none", "None", None}

parser = argparse.ArgumentParser(description="SE-NF cached 7d load forecast from Home Assistant recorder SQLite DB.")
parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to Home Assistant recorder SQLite DB")
parser.add_argument("--entity", default="", help="Daily consumption entity_id, e.g. sensor.gesamtverbrauch_tag")
args = parser.parse_args()

db_arg = (args.db or "").strip()
entity_arg = (args.entity or "").strip()

DB = Path(db_arg) if db_arg not in BAD else DEFAULT_DB
ENTITY = entity_arg if entity_arg not in BAD else ""

def out(data):
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

def zero(valid=False, error=None):
    data = {
        "remaining": 0.0,
        "until_now": 0.0,
        "avg_day_total": 0.0,
        "min_remaining": 0.0,
        "max_remaining": 0.0,
        "days": 0,
        "samples_total": 0,
        "valid": valid,
        "source": "sqlite_cached",
        "duration_ms": 0,
    }
    if error:
        data["error"] = str(error)[:180]
    out(data)

start = time.time()

if not ENTITY or "." not in ENTITY:
    zero(False, "entity not configured")
    sys.exit(0)

if not DB.exists():
    zero(False, "DB not found")
    sys.exit(0)

try:
    con = sqlite3.connect(f"file:{DB}?mode=ro&cache=shared", uri=True, timeout=10)
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA busy_timeout=10000")

    cur = con.cursor()
    cur.execute("SELECT metadata_id FROM states_meta WHERE entity_id = ? LIMIT 1", (ENTITY,))
    row = cur.fetchone()
    if not row:
        zero(False, "metadata_id not found")
        sys.exit(0)

    metadata_id = row[0]

    query = """
      WITH params AS (
        SELECT time('now','localtime') AS now_time
      ),
      daily_values AS (
        SELECT
          date(datetime(s.last_updated_ts, 'unixepoch', 'localtime')) AS tag,
          time(datetime(s.last_updated_ts, 'unixepoch', 'localtime')) AS uhrzeit,
          CAST(s.state AS REAL) AS val
        FROM states s
        WHERE s.metadata_id = ?
          AND s.last_updated_ts >= strftime('%s','now','-14 days')
          AND s.state NOT IN ('unknown','unavailable','none','')
          AND date(datetime(s.last_updated_ts, 'unixepoch', 'localtime')) < date('now','localtime')
      ),
      per_day_all AS (
        SELECT
          dv.tag,
          MAX(dv.val) AS day_end,
          (
            SELECT dv2.val
            FROM daily_values dv2, params p
            WHERE dv2.tag = dv.tag
              AND dv2.uhrzeit >= p.now_time
            ORDER BY dv2.uhrzeit ASC
            LIMIT 1
          ) AS value_at_nowtime,
          COUNT(*) AS samples
        FROM daily_values dv
        GROUP BY dv.tag
        HAVING COUNT(*) >= 6
      ),
      selected_days AS (
        SELECT *
        FROM per_day_all
        WHERE value_at_nowtime IS NOT NULL
          AND day_end IS NOT NULL
          AND day_end >= value_at_nowtime
          AND day_end >= 1
          AND day_end < 80
        ORDER BY tag DESC
        LIMIT 7
      )
      SELECT
        ROUND(COALESCE(AVG(day_end - value_at_nowtime), 0), 2) AS remaining,
        ROUND(COALESCE(AVG(value_at_nowtime), 0), 2) AS until_now,
        ROUND(COALESCE(AVG(day_end), 0), 2) AS avg_day_total,
        ROUND(COALESCE(MIN(day_end - value_at_nowtime), 0), 2) AS min_remaining,
        ROUND(COALESCE(MAX(day_end - value_at_nowtime), 0), 2) AS max_remaining,
        CAST(COALESCE(COUNT(*), 0) AS INTEGER) AS days,
        CAST(COALESCE(SUM(samples), 0) AS INTEGER) AS samples_total
      FROM selected_days;
    """

    cur.execute(query, (metadata_id,))
    r = cur.fetchone()

    duration_ms = int((time.time() - start) * 1000)

    if not r:
        zero(False, "empty result")
        sys.exit(0)

    data = {
        "remaining": float(r[0] or 0),
        "until_now": float(r[1] or 0),
        "avg_day_total": float(r[2] or 0),
        "min_remaining": float(r[3] or 0),
        "max_remaining": float(r[4] or 0),
        "days": int(r[5] or 0),
        "samples_total": int(r[6] or 0),
        "valid": int(r[5] or 0) > 0,
        "source": "sqlite_cached",
        "duration_ms": duration_ms,
    }
    out(data)

except Exception as e:
    data = {
        "remaining": 0.0,
        "until_now": 0.0,
        "avg_day_total": 0.0,
        "min_remaining": 0.0,
        "max_remaining": 0.0,
        "days": 0,
        "samples_total": 0,
        "valid": False,
        "source": "sqlite_cached",
        "duration_ms": int((time.time() - start) * 1000),
        "error": str(e)[:180],
    }
    out(data)
