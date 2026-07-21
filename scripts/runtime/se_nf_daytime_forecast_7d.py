#!/usr/bin/env python3
import argparse
import json
import math
import sqlite3
import statistics
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def decimal_hour_to_text(value):
    hour = int(value)
    minute = int(round((value - hour) * 60))
    if minute >= 60:
        hour += 1
        minute -= 60
    return f"{hour % 24:02d}:{minute:02d}"


def datetime_for_hour(day, decimal_hour, tz):
    hour = int(decimal_hour)
    minute = int(round((decimal_hour - hour) * 60))
    if minute >= 60:
        hour += 1
        minute -= 60
    return datetime(
        day.year,
        day.month,
        day.day,
        hour % 24,
        minute,
        tzinfo=tz,
    )


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--start-hour", type=float, default=8.0)
    parser.add_argument("--end-hour", type=float, default=18.5)
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--unit", default="kWh")
    parser.add_argument("--minimum-days", type=int, default=3)
    parser.add_argument("--history-days", type=int, default=14)
    args = parser.parse_args()

    try:
        local_tz = ZoneInfo(args.timezone)
    except Exception:
        local_tz = timezone.utc

    payload = {
        "value_kwh": 0,
        "valid": False,
        "source": "unavailable",
        "valid_days": 0,
        "minimum_kwh": None,
        "maximum_kwh": None,
        "mean_kwh": None,
        "median_kwh": None,
        "window_start": decimal_hour_to_text(args.start_hour),
        "window_end": decimal_hour_to_text(args.end_hour),
        "day_values": [],
        "error": "",
    }

    if not args.entity or args.entity.lower() in {
        "unknown",
        "unavailable",
        "none",
    }:
        payload["error"] = "daily_consumption_entity_missing"
        emit(payload)
        return

    unit = args.unit.strip().lower()
    scale = 0.001 if unit == "wh" else 1000.0 if unit == "mwh" else 1.0
    now_local = datetime.now(local_tz)
    cutoff = now_local - timedelta(days=max(args.history_days, 10))
    cutoff_ts = cutoff.astimezone(timezone.utc).timestamp()

    try:
        quoted = urllib.parse.quote(args.db, safe="/:")
        connection = sqlite3.connect(
            f"file:{quoted}?mode=ro",
            uri=True,
            timeout=20,
        )
    except Exception as exc:
        payload["error"] = f"database_open_failed:{type(exc).__name__}"
        emit(payload)
        return

    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(states)")
        }
        if "states" not in tables or "last_updated_ts" not in columns:
            raise RuntimeError("unsupported_recorder_schema")

        ts_expr = (
            "COALESCE(last_updated_ts,last_changed_ts)"
            if "last_changed_ts" in columns
            else "last_updated_ts"
        )

        if "states_meta" in tables and "metadata_id" in columns:
            metadata = connection.execute(
                "SELECT metadata_id FROM states_meta WHERE entity_id=?",
                (args.entity,),
            ).fetchone()
            if metadata is None:
                raise RuntimeError("entity_not_found_in_recorder")
            rows = connection.execute(
                f"SELECT state,{ts_expr} FROM states "
                f"WHERE metadata_id=? AND {ts_expr}>=? ORDER BY {ts_expr}",
                (metadata[0], cutoff_ts),
            ).fetchall()
        else:
            rows = connection.execute(
                f"SELECT state,{ts_expr} FROM states "
                f"WHERE entity_id=? AND {ts_expr}>=? ORDER BY {ts_expr}",
                (args.entity, cutoff_ts),
            ).fetchall()
    except Exception as exc:
        payload["error"] = str(exc)
        emit(payload)
        return
    finally:
        connection.close()

    points = []
    for raw_state, raw_timestamp in rows:
        try:
            value = float(raw_state) * scale
            timestamp = float(raw_timestamp)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or not math.isfinite(timestamp) or value < 0:
            continue
        recorded_at = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).astimezone(local_tz)
        points.append((recorded_at, value))

    def last_value(day, target):
        result = None
        for recorded_at, value in points:
            if recorded_at.date() == day and recorded_at <= target:
                result = value
        return result

    records = []
    for days_back in range(max(args.history_days, 10), 0, -1):
        day = now_local.date() - timedelta(days=days_back)
        start = datetime_for_hour(day, args.start_hour, local_tz)
        end = datetime_for_hour(day, args.end_hour, local_tz)
        if end <= start or end > now_local:
            continue
        start_value = last_value(day, start)
        end_value = last_value(day, end)
        if start_value is None or end_value is None:
            continue
        consumption = end_value - start_value
        if (
            not math.isfinite(consumption)
            or consumption < -0.05
            or consumption > 50
        ):
            continue
        records.append(
            {
                "date": day.isoformat(),
                "kwh": round(max(consumption, 0), 2),
            }
        )

    records = records[-7:]
    values = [record["kwh"] for record in records]
    payload["valid_days"] = len(values)
    payload["day_values"] = records

    if values:
        payload["minimum_kwh"] = round(min(values), 2)
        payload["maximum_kwh"] = round(max(values), 2)
        payload["mean_kwh"] = round(statistics.mean(values), 2)
        payload["median_kwh"] = round(statistics.median(values), 2)

    if len(values) >= max(args.minimum_days, 1):
        payload["value_kwh"] = payload["median_kwh"]
        payload["valid"] = True
        payload["source"] = "median_7_day_windows"
    elif not points:
        payload["error"] = "no_numeric_recorder_samples"
    else:
        payload["error"] = "insufficient_daytime_history"

    emit(payload)


if __name__ == "__main__":
    main()
