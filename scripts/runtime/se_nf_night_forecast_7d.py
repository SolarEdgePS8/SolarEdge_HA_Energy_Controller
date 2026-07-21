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


def percentile(values, fraction):
    """Return a linearly interpolated percentile for finite values."""
    ordered = []

    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue

        if math.isfinite(parsed):
            ordered.append(parsed)

    ordered.sort()

    if not ordered:
        return None

    if len(ordered) == 1:
        return ordered[0]

    fraction = min(max(float(fraction), 0.0), 1.0)
    rank = (len(ordered) - 1) * fraction
    lower = math.floor(rank)
    upper = math.ceil(rank)

    if lower == upper:
        return ordered[lower]

    weight = rank - lower
    return (
        ordered[lower] * (1.0 - weight)
        + ordered[upper] * weight
    )


def datetime_for_hour(day, decimal_hour, tz):
    hour = int(decimal_hour)
    minute = int(round((decimal_hour - hour) * 60))
    if minute >= 60:
        hour += 1
        minute -= 60
    return datetime(
        day.year, day.month, day.day,
        hour % 24, minute, 0,
        tzinfo=tz,
    )


def output(payload):
    print(json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--start-hour", type=float, default=18.5)
    parser.add_argument("--end-hour", type=float, default=8.0)
    parser.add_argument(
        "--morning-checkpoint-hour",
        type=float,
        default=6.0,
    )
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--unit", default="kWh")
    parser.add_argument("--fallback", type=float, default=4.5)
    parser.add_argument("--minimum-nights", type=int, default=3)
    parser.add_argument("--history-days", type=int, default=14)
    args = parser.parse_args()

    try:
        local_tz = ZoneInfo(args.timezone)
    except Exception:
        local_tz = timezone.utc

    unit = args.unit.strip().lower()
    if unit == "wh":
        scale_to_kwh = 0.001
    elif unit == "mwh":
        scale_to_kwh = 1000.0
    else:
        scale_to_kwh = 1.0

    now_local = datetime.now(local_tz)
    history_days = max(args.history_days, 10)
    cutoff = now_local - timedelta(days=history_days)
    cutoff_ts = cutoff.astimezone(timezone.utc).timestamp()

    payload = {
        "value_kwh": round(max(args.fallback, 0), 2),
        "valid": False,
        "source": "fallback",
        "valid_nights": 0,
        "minimum_kwh": None,
        "maximum_kwh": None,
        "mean_kwh": None,
        "median_kwh": None,
        "p80_kwh": None,
        "window_start": decimal_hour_to_text(args.start_hour),
        "window_end": decimal_hour_to_text(args.end_hour),
        "morning_checkpoint": decimal_hour_to_text(
            args.morning_checkpoint_hour
        ),
        "morning_window_hours": round(
            max(
                args.end_hour
                - min(args.morning_checkpoint_hour, args.end_hour),
                0,
            ),
            2,
        ),
        "morning_valid_nights": 0,
        "morning_median_kwh": None,
        "morning_p80_kwh": None,
        "night_values": [],
        "morning_values": [],
        "error": "",
    }

    bad = {"", "unknown", "unavailable", "none"}

    if not args.entity or args.entity.lower() in bad:
        payload["error"] = "daily_consumption_entity_missing"
        output(payload)
        return

    try:
        quoted_path = urllib.parse.quote(args.db, safe="/:")
        connection = sqlite3.connect(
            f"file:{quoted_path}?mode=ro",
            uri=True,
            timeout=20,
        )
    except Exception as exc:
        payload["error"] = (
            f"database_open_failed:{type(exc).__name__}"
        )
        output(payload)
        return

    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(states)"
            )
        }

        if (
            "states" not in tables
            or "last_updated_ts" not in columns
        ):
            raise RuntimeError("unsupported_recorder_schema")

        if "last_changed_ts" in columns:
            ts_expr = (
                "COALESCE(last_updated_ts,last_changed_ts)"
            )
        else:
            ts_expr = "last_updated_ts"

        if (
            "states_meta" in tables
            and "metadata_id" in columns
        ):
            metadata = connection.execute(
                "SELECT metadata_id FROM states_meta "
                "WHERE entity_id=?",
                (args.entity,),
            ).fetchone()

            if metadata is None:
                raise RuntimeError(
                    "entity_not_found_in_recorder"
                )

            rows = connection.execute(
                f"SELECT state,{ts_expr} FROM states "
                f"WHERE metadata_id=? "
                f"AND {ts_expr}>=? "
                f"ORDER BY {ts_expr}",
                (metadata[0], cutoff_ts),
            ).fetchall()
        else:
            rows = connection.execute(
                f"SELECT state,{ts_expr} FROM states "
                f"WHERE entity_id=? "
                f"AND {ts_expr}>=? "
                f"ORDER BY {ts_expr}",
                (args.entity, cutoff_ts),
            ).fetchall()

    except Exception as exc:
        payload["error"] = str(exc)
        output(payload)
        return
    finally:
        connection.close()

    points = []

    for raw_state, raw_timestamp in rows:
        try:
            value = float(raw_state) * scale_to_kwh
            timestamp = float(raw_timestamp)
        except (TypeError, ValueError):
            continue

        if (
            not math.isfinite(value)
            or not math.isfinite(timestamp)
            or value < 0
        ):
            continue

        recorded_at = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).astimezone(local_tz)

        points.append((recorded_at, value))

    def last_value_on_day(day, target):
        result = None

        for recorded_at, value in points:
            if (
                recorded_at.date() == day
                and recorded_at <= target
            ):
                result = value

        return result

    records = []
    morning_records = []

    for days_back in range(history_days, 0, -1):
        evening_day = (
            now_local.date() - timedelta(days=days_back)
        )
        morning_day = evening_day + timedelta(days=1)

        evening_time = datetime_for_hour(
            evening_day,
            args.start_hour,
            local_tz,
        )

        end_of_day = datetime(
            evening_day.year,
            evening_day.month,
            evening_day.day,
            23, 59, 59,
            tzinfo=local_tz,
        )

        morning_time = datetime_for_hour(
            morning_day,
            args.end_hour,
            local_tz,
        )

        checkpoint_hour = min(
            args.morning_checkpoint_hour,
            args.end_hour,
        )
        morning_checkpoint_time = datetime_for_hour(
            morning_day,
            checkpoint_hour,
            local_tz,
        )

        if morning_time > now_local:
            continue

        evening_value = last_value_on_day(
            evening_day,
            evening_time,
        )
        day_total = last_value_on_day(
            evening_day,
            end_of_day,
        )
        morning_value = last_value_on_day(
            morning_day,
            morning_time,
        )
        morning_checkpoint_value = last_value_on_day(
            morning_day,
            morning_checkpoint_time,
        )

        if (
            evening_value is None
            or day_total is None
            or morning_value is None
        ):
            continue

        evening_part = day_total - evening_value

        if evening_part < -0.05:
            continue

        total = (
            max(evening_part, 0)
            + max(morning_value, 0)
        )

        if (
            not math.isfinite(total)
            or total < 0
            or total > 50
        ):
            continue

        date_label = (
            f"{evening_day.isoformat()}"
            f"→{morning_day.isoformat()}"
        )

        records.append({
            "date": date_label,
            "kwh": round(total, 2),
        })

        if morning_checkpoint_value is not None:
            morning_segment = (
                morning_value - morning_checkpoint_value
            )

            if morning_segment >= -0.05:
                morning_segment = max(morning_segment, 0)

                if (
                    math.isfinite(morning_segment)
                    and morning_segment <= 20
                ):
                    morning_records.append({
                        "date": date_label,
                        "kwh": round(morning_segment, 2),
                    })

    records = records[-7:]
    morning_records = morning_records[-7:]

    values = [record["kwh"] for record in records]
    morning_values = [
        record["kwh"]
        for record in morning_records
    ]

    payload["valid_nights"] = len(values)
    payload["night_values"] = records
    payload["morning_valid_nights"] = len(morning_values)
    payload["morning_values"] = morning_records

    if values:
        payload["minimum_kwh"] = round(min(values), 2)
        payload["maximum_kwh"] = round(max(values), 2)
        payload["mean_kwh"] = round(
            statistics.mean(values), 2
        )
        payload["median_kwh"] = round(
            statistics.median(values), 2
        )
        payload["p80_kwh"] = round(
            percentile(values, 0.80), 2
        )

    if morning_values:
        payload["morning_median_kwh"] = round(
            statistics.median(morning_values), 2
        )
        payload["morning_p80_kwh"] = round(
            percentile(morning_values, 0.80), 2
        )

    if len(values) >= max(args.minimum_nights, 1):
        payload["value_kwh"] = payload["median_kwh"]
        payload["valid"] = True
        payload["source"] = "median_7_nights"
    elif not points:
        payload["error"] = "no_numeric_recorder_samples"
    else:
        payload["error"] = "insufficient_night_history"

    output(payload)


if __name__ == "__main__":
    main()
