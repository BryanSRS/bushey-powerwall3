"""SQLite storage for readings."""
import os
import sqlite3
import threading

from .powerwall import Snapshot


class Storage:
    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS readings (
                    ts REAL PRIMARY KEY,
                    solar_w REAL, battery_w REAL, grid_w REAL, home_w REAL,
                    battery_pct REAL, grid_status TEXT
                )"""
            )
            self.conn.commit()

    def insert(self, s: Snapshot) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO readings VALUES (?, ?, ?, ?, ?, ?, ?)",
                (s.ts, s.solar_w, s.battery_w, s.grid_w, s.home_w, s.battery_pct, s.grid_status),
            )
            self.conn.commit()

    def history(self, since_ts: float, bucket_seconds: int) -> list[dict]:
        """Readings since `since_ts`, averaged into buckets of `bucket_seconds`."""
        with self.lock:
            rows = self.conn.execute(
                """SELECT CAST(ts / ? AS INTEGER) * ? AS bucket,
                          AVG(solar_w), AVG(battery_w), AVG(grid_w), AVG(home_w), AVG(battery_pct)
                   FROM readings WHERE ts >= ?
                   GROUP BY bucket ORDER BY bucket""",
                (bucket_seconds, bucket_seconds, since_ts),
            ).fetchall()
        keys = ("ts", "solar_w", "battery_w", "grid_w", "home_w", "battery_pct")
        return [dict(zip(keys, (round(v, 1) for v in r))) for r in rows]
