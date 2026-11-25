# Bushey Powerwall data screen

A home-built screen for the Powerwall 3: live solar, house, battery and grid readings, plus a 24-hour history, served from the ThinkCentre to any browser on the home network.

It reads the Powerwall locally with [pyPowerwall](https://github.com/jasonacox/pypowerwall), stores every reading in SQLite, and serves a small web page and JSON API with FastAPI.

## Layout

```
app/
  config.py      settings from .env
  powerwall.py   data sources: real Powerwall (TEDAPI) or mock
  collector.py   background polling loop
  storage.py     SQLite readings + history queries
  main.py        web server and API
  static/        the data screen page
deploy/
  powerwall-screen.service   systemd unit for always-on running
```

## Try it with sample data (any PC)

```bash
git clone https://github.com/BryanSRS/bushey-powerwall3.git
cd bushey-powerwall3
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # PW_MODE=mock by default
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080.

## Connect the real Powerwall (ThinkCentre)

Since Powerwall firmware 25.10, local data is only reachable while joined to the Powerwall's own Wi-Fi network. The plan is Ethernet for the home network and the built-in Wi-Fi for the Powerwall.

1. Join the Powerwall's Wi-Fi (`TeslaPW_…`) using the password on its label.
2. Keep Ethernet as the default route so the internet doesn't go through the Powerwall:
   ```bash
   nmcli connection modify "TeslaPW_XXXXXX" ipv4.never-default yes
   nmcli connection up "TeslaPW_XXXXXX"
   ```
3. Check it's reachable: `ping 192.168.91.1`
4. In `.env`, set `PW_MODE=tedapi` and `PW_GW_PASSWORD` to the label password.
5. Restart the app. The footer note about sample data disappears once it's reading the Powerwall.

## Run it all the time

```bash
sudo cp deploy/powerwall-screen.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now powerwall-screen
journalctl -u powerwall-screen -f    # logs
```

Edit `User=` and the paths in the service file first if you didn't clone to `/opt/bushey-powerwall3`.

## API

| Endpoint | Returns |
|---|---|
| `/api/live` | Latest reading, with `stale` set if readings have stopped |
| `/api/history?hours=24` | Averaged readings for charts |
| `/api/strings` | Per-string solar voltage, current and power |
| `/api/health` | Mode and last error |

Sign conventions follow pyPowerwall: battery positive means discharging, grid positive means buying from the grid.

## Secrets

`.env` and pyPowerwall's auth/cache files are in `.gitignore`. This repo is public, so keep passwords and tokens out of anything you commit.
