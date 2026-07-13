"""CLI: render Singapore building footprint maps from sg-old Ontop."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from mini_marie.zaha.sg_old.gis_visualization import generate_footprint_map, summarize_footprints


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize sg-old building footprints on a Leaflet map")
    parser.add_argument("--name", default="Abbott", help="Facility name fragment (default: Abbott)")
    parser.add_argument("--output", type=str, help="Output HTML path")
    parser.add_argument("--open", action="store_true", help="Open map in default browser")
    args = parser.parse_args()

    path, rows, _geojson = generate_footprint_map(
        args.name,
        output_path=Path(args.output) if args.output else None,
    )
    print(f"Map: {path.resolve()}")
    print(summarize_footprints(rows))
    if args.open:
        webbrowser.open(path.resolve().as_uri())


if __name__ == "__main__":
    main()
