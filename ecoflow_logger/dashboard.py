"""Generates the static HTML dashboard pages and service worker for however
many devices are configured, so adding a device means adding a serial number
to one secret rather than hand-writing a new page.

Device 1 keeps the original file names (``index.html``, ``data/ecoflow_log.csv``,
``data/ecoflow_plot.png``) so existing links and bookmarks keep working;
device N (N >= 2) gets ``deviceN.html`` / ``data/ecoflow_log_N.csv`` /
``data/ecoflow_plot_N.png``.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

DEFAULT_TITLE = "EcoFlow DELTA 2 Max"


class DeviceSpec(NamedTuple):
    index: int  # 1-based
    title: str
    html_name: str
    csv_path: str  # relative to the pages directory, e.g. "data/ecoflow_log.csv"
    png_path: str


def build_device_specs(sns: list[str]) -> list[DeviceSpec]:
    """One DeviceSpec per non-empty, whitespace-trimmed serial number."""
    specs = []
    for index, _sn in enumerate((sn.strip() for sn in sns if sn.strip()), start=1):
        if index == 1:
            specs.append(
                DeviceSpec(1, DEFAULT_TITLE, "index.html", "data/ecoflow_log.csv", "data/ecoflow_plot.png")
            )
        else:
            specs.append(
                DeviceSpec(
                    index,
                    f"EcoFlow Device {index}",
                    f"device{index}.html",
                    f"data/ecoflow_log_{index}.csv",
                    f"data/ecoflow_plot_{index}.png",
                )
            )
    return specs


def _nav_html(spec: DeviceSpec, all_specs: list[DeviceSpec]) -> str:
    others = [s for s in all_specs if s.index != spec.index]
    if not others:
        return ""
    links = " &middot; ".join(f'<a href="{s.html_name}">{s.title} &rarr;</a>' for s in others)
    return f" &middot; {links}"


_PAGE_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<meta name="theme-color" content="#2a78d6">
<style>
  :root {{
    color-scheme: light dark;
    --surface: #fcfcfb;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --border: #e1e0d9;
    --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface: #1a1a19;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --border: #2c2c2a;
      --accent: #3987e5;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px 16px 48px;
    background: var(--surface);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    display: flex;
    justify-content: center;
  }}
  main {{ width: 100%; max-width: 900px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  p.subtitle {{ color: var(--text-secondary); margin: 0 0 24px; font-size: 14px; }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .stat {{
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
  }}
  .stat .label {{
    color: var(--text-muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }}
  .stat .value {{
    font-size: 24px;
    font-weight: 600;
    margin-top: 4px;
  }}
  img {{
    width: 100%;
    height: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    display: block;
  }}
  .updated {{
    margin-top: 12px;
    color: var(--text-muted);
    font-size: 13px;
  }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">Charge and power, logged every 5 minutes by <a href="https://github.com/camsonne/Ecoflow2logger">GitHub Actions</a>.{nav_html}</p>

  <div class="stats" id="stats">
    <div class="stat"><div class="label">Charge</div><div class="value" id="stat-soc">–</div></div>
    <div class="stat"><div class="label">Power in</div><div class="value" id="stat-in">–</div></div>
    <div class="stat"><div class="label">Power out</div><div class="value" id="stat-out">–</div></div>
    <div class="stat extra-stat" id="tile-extra-soc" hidden><div class="label">Extra battery charge</div><div class="value" id="stat-extra-soc">–</div></div>
    <div class="stat extra-stat" id="tile-extra-in" hidden><div class="label">Extra battery power in</div><div class="value" id="stat-extra-in">–</div></div>
    <div class="stat extra-stat" id="tile-extra-out" hidden><div class="label">Extra battery power out</div><div class="value" id="stat-extra-out">–</div></div>
    <div class="stat pv-stat" id="tile-pv1" hidden><div class="label">Solar 1</div><div class="value" id="stat-pv1">–</div></div>
    <div class="stat pv-stat" id="tile-pv2" hidden><div class="label">Solar 2</div><div class="value" id="stat-pv2">–</div></div>
  </div>

  <img src="{png_path}" alt="{title} charge and power chart" id="chart">
  <p class="updated" id="updated">Loading latest reading…</p>
</main>
<script>
  // Bust caches so the page always shows the latest committed chart/data,
  // and reload periodically so the tab stays live without manual refresh.
  const bust = "?t=" + Date.now();
  document.getElementById("chart").src = "{png_path}" + bust;

  fetch("{csv_path}" + bust)
    .then((r) => r.text())
    .then((text) => {{
      const lines = text.trim().split(/\\r\\n|\\n/);
      if (lines.length < 2) return;
      const header = lines[0].split(",");
      const last = lines[lines.length - 1].split(",");
      const row = Object.fromEntries(header.map((h, i) => [h, last[i]]));

      document.getElementById("stat-soc").textContent =
        row.soc_percent ? `${{Number(row.soc_percent).toFixed(0)}}%` : "–";
      document.getElementById("stat-in").textContent =
        row.watts_in ? `${{Number(row.watts_in).toFixed(0)}} W` : "–";
      document.getElementById("stat-out").textContent =
        row.watts_out ? `${{Number(row.watts_out).toFixed(0)}} W` : "–";

      // Extra-battery tiles only exist for setups that have one; the CSV
      // simply won't have these values for everyone else's chart.
      const hasExtraBattery =
        row.extra_battery_soc_percent || row.extra_battery_watts_in || row.extra_battery_watts_out;
      document.querySelectorAll(".extra-stat").forEach((el) => (el.hidden = !hasExtraBattery));
      if (hasExtraBattery) {{
        document.getElementById("stat-extra-soc").textContent =
          row.extra_battery_soc_percent ? `${{Number(row.extra_battery_soc_percent).toFixed(0)}}%` : "–";
        document.getElementById("stat-extra-in").textContent =
          row.extra_battery_watts_in ? `${{Number(row.extra_battery_watts_in).toFixed(0)}} W` : "–";
        document.getElementById("stat-extra-out").textContent =
          row.extra_battery_watts_out ? `${{Number(row.extra_battery_watts_out).toFixed(0)}} W` : "–";
      }}

      // PV tiles only exist for setups with solar panels; the CSV simply
      // won't have these values for everyone else's chart.
      const hasPv = row.pv1_watts || row.pv2_watts;
      document.querySelectorAll(".pv-stat").forEach((el) => (el.hidden = !hasPv));
      if (hasPv) {{
        document.getElementById("stat-pv1").textContent =
          row.pv1_watts ? `${{Number(row.pv1_watts).toFixed(0)}} W` : "–";
        document.getElementById("stat-pv2").textContent =
          row.pv2_watts ? `${{Number(row.pv2_watts).toFixed(0)}} W` : "–";
      }}

      const lastReadingEt = new Date(row.timestamp).toLocaleString("en-US", {{
        timeZone: "America/New_York",
        dateStyle: "medium",
        timeStyle: "medium",
      }});
      document.getElementById("updated").textContent =
        `Last reading: ${{lastReadingEt}} ET (page loaded ${{new Date().toLocaleString()}})`;
    }})
    .catch(() => {{
      document.getElementById("updated").textContent =
        "No data yet — waiting on the first workflow run.";
    }});

  setInterval(() => location.reload(), 2 * 60 * 1000);

  if ("serviceWorker" in navigator) {{
    window.addEventListener("load", () => {{
      navigator.serviceWorker.register("sw.js").catch(() => {{}});
    }});
  }}
</script>
</body>
</html>
"""


def render_dashboard_html(spec: DeviceSpec, all_specs: list[DeviceSpec]) -> str:
    return _PAGE_TEMPLATE.format(
        title=spec.title,
        nav_html=_nav_html(spec, all_specs),
        png_path=spec.png_path,
        csv_path=spec.csv_path,
    )


_SW_TEMPLATE = """\
// Minimal service worker: makes the dashboard installable as a PWA and
// lets it open offline (showing the last-cached reading) if there's no
// connection. Deliberately no full offline-first app — this is a live
// dashboard, so data/ files are always fetched from the network first.
//
// Generated by ecoflow_logger.dashboard from the configured device list --
// edit ECOFLOW_DEVICE_SNS, not this file, to add or remove a device.
const CACHE = "ecoflow-dashboard-v1";
const APP_SHELL = [
  "./",
{app_shell_entries}
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {{
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
}});

self.addEventListener("fetch", (event) => {{
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  const isData = url.pathname.includes("/data/");

  if (isData) {{
    // Network-first: always prefer a fresh chart/CSV, cache it for
    // offline viewing, fall back to whatever was last cached. index.html
    // cache-busts these requests with a ?t= query param, so cache under
    // the bare path (ignoring the query) or every load would miss.
    const cacheKey = new Request(url.origin + url.pathname);
    event.respondWith(
      fetch(event.request)
        .then((response) => {{
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(cacheKey, copy));
          return response;
        }})
        .catch(() => caches.match(cacheKey))
    );
    return;
  }}

  // App shell: cache-first, network as fallback.
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
}});
"""


def render_service_worker(all_specs: list[DeviceSpec]) -> str:
    entries = "\n".join(f'  "./{spec.html_name}",' for spec in all_specs)
    return _SW_TEMPLATE.format(app_shell_entries=entries)


def write_dashboards(sns: list[str], out_dir: Path) -> list[Path]:
    """Render index.html/deviceN.html + sw.js for the given devices.

    Returns the list of paths written, for the caller to `git add`.
    """
    specs = build_device_specs(sns)
    if not specs:
        raise ValueError("no device serial numbers given")

    written = []
    for spec in specs:
        path = out_dir / spec.html_name
        path.write_text(render_dashboard_html(spec, specs))
        written.append(path)

    sw_path = out_dir / "sw.js"
    sw_path.write_text(render_service_worker(specs))
    written.append(sw_path)

    return written
