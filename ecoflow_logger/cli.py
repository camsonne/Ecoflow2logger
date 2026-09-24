"""Command line interface: `python -m ecoflow_logger <log|plot> ...`"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .api import DEFAULT_BASE_URL, EcoFlowClient
from .dashboard import write_dashboards
from .logger import run_logger
from .plot import plot_csv


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecoflow_logger",
        description="Log and plot EcoFlow DELTA 2 Max charge % and power in/out over time.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    log_parser = sub.add_parser("log", help="Poll the device and append readings to a CSV file")
    log_parser.add_argument("--sn", required=True, help="Device serial number")
    log_parser.add_argument(
        "--access-key", default=os.environ.get("ECOFLOW_ACCESS_KEY"),
        help="EcoFlow Open API access key (env: ECOFLOW_ACCESS_KEY)",
    )
    log_parser.add_argument(
        "--secret-key", default=os.environ.get("ECOFLOW_SECRET_KEY"),
        help="EcoFlow Open API secret key (env: ECOFLOW_SECRET_KEY)",
    )
    log_parser.add_argument("--csv", default="ecoflow_log.csv", help="CSV file to append readings to")
    log_parser.add_argument(
        "--base-url", default=os.environ.get("ECOFLOW_BASE_URL") or DEFAULT_BASE_URL,
        help=(
            "EcoFlow Open API base URL (env: ECOFLOW_BASE_URL, default: "
            f"{DEFAULT_BASE_URL}). EcoFlow accounts are region-locked to a "
            "specific API host (e.g. api-a.ecoflow.com for the Americas vs "
            "api-e.ecoflow.com for Europe) — 'accessKey is invalid' with a "
            "key you're sure is correct usually means this is set to the "
            "wrong region."
        ),
    )
    log_parser.add_argument("--interval", type=float, default=60.0, help="Seconds between polls (default: 60)")
    log_parser.add_argument("--iterations", type=int, default=None, help="Stop after N polls (default: run forever)")
    log_parser.add_argument("-v", "--verbose", action="store_true", help="Enable info-level logging")

    plot_parser = sub.add_parser("plot", help="Plot a logged CSV file")
    plot_parser.add_argument("--csv", default="ecoflow_log.csv", help="CSV file to read readings from")
    plot_parser.add_argument("--out", default=None, help="Save the plot to this image file instead of showing it")
    plot_parser.add_argument("--title", default="EcoFlow DELTA 2 Max", help="Plot title")

    dashboards_parser = sub.add_parser(
        "dashboards",
        help="Render index.html/deviceN.html + sw.js for a list of devices",
    )
    dashboards_parser.add_argument(
        "--sns", required=True,
        help="Comma-separated device serial numbers, in device order (same value as ECOFLOW_DEVICE_SNS)",
    )
    dashboards_parser.add_argument(
        "--out-dir", default=".", help="Directory to write the HTML pages and sw.js into (default: current dir)"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "log":
        logging.basicConfig(
            level=logging.INFO if args.verbose else logging.WARNING,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        if not args.access_key or not args.secret_key:
            parser.error(
                "--access-key/--secret-key are required (or set ECOFLOW_ACCESS_KEY / ECOFLOW_SECRET_KEY)"
            )
        client = EcoFlowClient(args.access_key, args.secret_key, base_url=args.base_url)
        run_logger(client, args.sn, Path(args.csv), args.interval, args.iterations)
        return 0

    if args.command == "plot":
        out = Path(args.out) if args.out else None
        plot_csv(Path(args.csv), out, title=args.title)
        if out:
            print(f"Wrote {out}")
        return 0

    if args.command == "dashboards":
        sns = args.sns.split(",")
        written = write_dashboards(sns, Path(args.out_dir))
        for path in written:
            print(f"Wrote {path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
