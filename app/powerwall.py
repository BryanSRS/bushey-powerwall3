"""Data sources: the real Powerwall (via pyPowerwall) or a mock for development.

Sign conventions (same as pyPowerwall):
  solar_w   + producing
  battery_w + discharging (powering the house), - charging
  grid_w    + importing from the grid, - exporting to the grid
  home_w    + house consumption
"""
import logging
import math
import random
import time
from dataclasses import asdict, dataclass

from .config import settings

log = logging.getLogger(__name__)


@dataclass
class Snapshot:
    ts: float
    solar_w: float
    battery_w: float
    grid_w: float
    home_w: float
    battery_pct: float
    grid_status: str

    def to_dict(self) -> dict:
        return asdict(self)


class PowerwallSource:
    """Reads a Powerwall 3 locally in TEDAPI mode.

    The machine running this must be joined to the Powerwall's own Wi-Fi
    access point (firmware 25.10+ no longer routes 192.168.91.1 over the LAN).
    """

    def __init__(self) -> None:
        import pypowerwall  # imported here so mock mode works without it configured

        if not settings.gw_password:
            raise RuntimeError("PW_GW_PASSWORD is empty; set it in .env")
        log.info("Connecting to Powerwall at %s (TEDAPI)", settings.host)
        self.pw = pypowerwall.Powerwall(
            host=settings.host,
            password="",
            email="nobody@nowhere.com",
            timezone=settings.timezone,
            gw_pwd=settings.gw_password,
        )
        if not self.pw.is_connected():
            raise RuntimeError(f"Could not connect to Powerwall at {settings.host}")

    def read(self) -> Snapshot:
        p = self.pw.power() or {}
        return Snapshot(
            ts=time.time(),
            solar_w=float(p.get("solar") or 0),
            battery_w=float(p.get("battery") or 0),
            grid_w=float(p.get("site") or 0),
            home_w=float(p.get("load") or 0),
            battery_pct=float(self.pw.level() or 0),
            grid_status=str(self.pw.grid_status() or "UNKNOWN"),
        )

    def strings(self) -> dict:
        return self.pw.strings() or {}


class MockSource:
    """Fake but plausible data: a solar curve, a noisy house load, a battery that responds."""

    def __init__(self) -> None:
        self.battery_pct = 60.0
        self.last = time.time()

    def read(self) -> Snapshot:
        now = time.time()
        dt_h = (now - self.last) / 3600
        self.last = now

        hour = time.localtime(now).tm_hour + time.localtime(now).tm_min / 60
        solar = max(0.0, math.sin((hour - 6) / 13 * math.pi)) * 7000 * random.uniform(0.85, 1.0)
        home = 600 + random.uniform(0, 900) + (1500 if 17 <= hour <= 21 else 0)

        surplus = solar - home  # + means extra to put somewhere
        capacity_wh = 13500
        if surplus > 0 and self.battery_pct < 100:
            battery = -min(surplus, 5000)
        elif surplus < 0 and self.battery_pct > 20:
            battery = min(-surplus, 5000)
        else:
            battery = 0.0
        self.battery_pct = min(100.0, max(0.0, self.battery_pct - battery * dt_h / capacity_wh * 100))
        grid = home - solar - battery

        return Snapshot(now, round(solar), round(battery), round(grid), round(home),
                        round(self.battery_pct, 1), "UP")

    def strings(self) -> dict:
        return {
            "A": {"Connected": True, "Voltage": 380, "Current": 4.1, "Power": 1558},
            "B": {"Connected": True, "Voltage": 375, "Current": 3.9, "Power": 1462},
        }


def get_source():
    if settings.mode == "tedapi":
        return PowerwallSource()
    if settings.mode == "mock":
        return MockSource()
    raise ValueError(f"Unknown PW_MODE: {settings.mode!r} (use 'mock' or 'tedapi')")
