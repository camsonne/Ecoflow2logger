# Ecoflow2logger

Logs and plots battery charge percentage and power in/out over time for an
EcoFlow DELTA 2 Max, using the [EcoFlow Open Platform API](https://developer.ecoflow.com/us/document/generalInfo).

![Latest EcoFlow chart](data/ecoflow_plot.png)

*Auto-updated hourly by [`.github/workflows/log-and-plot.yml`](.github/workflows/log-and-plot.yml) — see [Automated logging on GitHub Actions](#automated-logging-on-github-actions) below. The image above is blank until that workflow's secrets are configured and it runs once.*

## Setup

```bash
pip install -r requirements.txt
```

Create an access key / secret key pair in the [EcoFlow IoT developer
portal](https://developer.ecoflow.com/), and find your device's serial
number (SN) in the EcoFlow app under device settings.

```bash
export ECOFLOW_ACCESS_KEY=...
export ECOFLOW_SECRET_KEY=...
```

EcoFlow accounts are region-locked to a specific API host. If you get
`EcoFlow API error (code='8513'): 'accessKey is invalid'` with a key you're
sure is correct, you're very likely on the wrong region's endpoint — set
`ECOFLOW_BASE_URL` (or pass `--base-url`) to the other one:

```bash
export ECOFLOW_BASE_URL=https://api-a.ecoflow.com  # Americas — default is api-e.ecoflow.com (Europe)
```

## Logging

Poll the device every 60 seconds and append readings to a CSV file:

```bash
python -m ecoflow_logger log --sn <DEVICE_SN> --csv ecoflow_log.csv --interval 60
```

Run `--iterations N` to stop after N polls instead of running forever (useful
for testing or a cron job). Add `-v` for progress logging.

Each row in the CSV has:

| column | meaning |
|---|---|
| `timestamp` | UTC timestamp (ISO 8601) of the poll |
| `soc_percent` | battery state of charge, % |
| `watts_in` | total power into the device, W |
| `watts_out` | total power out of the device, W |

A reading is skipped (left blank) if the corresponding quota field wasn't
present in that poll's response.

## Plotting

```bash
python -m ecoflow_logger plot --csv ecoflow_log.csv --out ecoflow_plot.png
```

Omit `--out` to open an interactive matplotlib window instead of saving a
file. This renders two panels sharing a time axis: charge % on top, power
in/out (as two separate lines) on the bottom — kept as two panels rather
than one chart with two y-axes, since state of charge and power are
different units and overlaying them on a shared scale would misrepresent
the trends.

## Automated logging on GitHub Actions

[`.github/workflows/log-and-plot.yml`](.github/workflows/log-and-plot.yml) polls
the device once an hour, regenerates the chart, and commits both
`data/ecoflow_log.csv` and `data/ecoflow_plot.png` back to the repository —
so the chart embedded at the top of this README always reflects the latest
reading. It also runs on demand via the "Run workflow" button under the
Actions tab.

To enable it, add these as repository secrets (Settings → Secrets and
variables → Actions):

| secret | value |
|---|---|
| `ECOFLOW_ACCESS_KEY` | your EcoFlow Open API access key |
| `ECOFLOW_SECRET_KEY` | your EcoFlow Open API secret key |
| `ECOFLOW_DEVICE_SN` | your device's serial number |

Scheduled (`cron`) workflows only fire from the repository's default branch,
so this starts running once the workflow file is merged there.

## Live dashboard (GitHub Pages)

[`index.html`](index.html) is a small static dashboard — stat tiles for the
latest charge/power reading plus the chart — that reads `data/ecoflow_log.csv`
and `data/ecoflow_plot.png` straight out of the repo, so it stays in sync with
every commit the Actions workflow above makes.

To publish it: **Settings → Pages → Build and deployment → Source: "Deploy
from a branch" → Branch: `main`, folder: `/ (root)` → Save.** GitHub then
serves it at `https://<owner>.github.io/<repo>/` and redeploys automatically
on every push to `main`, including the hourly data commits — no separate
Pages workflow needed.

## How it works

- `ecoflow_logger/api.py` — signs and sends requests to EcoFlow's
  `device/quota/all` endpoint, which returns every reported quota value for
  a device.
- `ecoflow_logger/metrics.py` — picks state-of-charge and power in/out out
  of the raw quota payload (field names vary slightly by firmware, so each
  metric has a small list of candidate keys).
- `ecoflow_logger/logger.py` — polls on an interval and appends rows to a
  CSV log, tolerating transient API/network failures.
- `ecoflow_logger/plot.py` — reads the CSV and renders the two-panel chart.

## Tests

```bash
pip install pytest
pytest
```

Tests cover the signing scheme, metric extraction, CSV logging, and chart
rendering — none require network access or a real device.
