"""Plot the Mw-Yb-Er efficiency-grid entanglement rate as a heatmap."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


EFFICIENCIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

DEFAULT_DATA_DIR = Path("tmp_mw_yb_er_efficiency_grid/efficiency_grid")
DEFAULT_OUTPUT = Path("tmp/mw_yb_er_efficiency_rate_heatmap.png")

LOG_NAME_RE = re.compile(
    r"uw_eff=([0-9.]+)_er_pce=([0-9.]+)\.log$"
)
ENTANGLEMENT_TIME_PATTERN = re.compile(
    r"Average three-node end-to-end entanglement time is\s*~\s*([-+0-9.eE]+)"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot the Mw-Yb-Er efficiency-grid entanglement rate."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing uw_eff=..._er_pce=....log files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output image path.",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Write the entanglement rate inside each heatmap cell.",
    )
    return parser.parse_args()


def read_entanglement_time(log_file: Path) -> float:
    """Read the final average entanglement time, in seconds, from a log."""

    value = None
    for line in log_file.read_text(errors="ignore").splitlines():
        match = ENTANGLEMENT_TIME_PATTERN.search(line)
        if match:
            value = float(match.group(1))
    if value is None:
        raise ValueError(f"Could not find average entanglement time in {log_file}")
    if value <= 0:
        raise ValueError(f"Entanglement time must be positive in {log_file}: {value}")
    return value


def load_rate_grid(data_dir: Path) -> np.ndarray:
    """Return rate=1/time with Mw efficiency rows and Er PCE columns."""

    if not data_dir.is_dir():
        raise FileNotFoundError(f"Efficiency-grid directory not found: {data_dir}")

    grid = np.full((len(EFFICIENCIES), len(EFFICIENCIES)), np.nan)
    efficiency_index = {
        value: index for index, value in enumerate(EFFICIENCIES)
    }

    for log_file in data_dir.glob("*.log"):
        match = LOG_NAME_RE.fullmatch(log_file.name)
        if not match:
            continue

        mw_efficiency = float(match.group(1))
        er_efficiency = float(match.group(2))
        if (
            mw_efficiency not in efficiency_index
            or er_efficiency not in efficiency_index
        ):
            continue

        entanglement_time = read_entanglement_time(log_file)
        grid[
            efficiency_index[mw_efficiency],
            efficiency_index[er_efficiency],
        ] = 1 / entanglement_time

    return grid


def plot_heatmap(grid: np.ndarray, output: Path, annotate: bool) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    masked_grid = np.ma.masked_invalid(grid)

    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad(color="#eeeeee")
    image = ax.imshow(masked_grid, cmap=cmap, aspect="auto", origin="lower")

    tick_positions = np.arange(len(EFFICIENCIES))
    tick_labels = [f"{value:.1f}" for value in EFFICIENCIES]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels)
    ax.set_yticks(tick_positions)
    ax.set_yticklabels(tick_labels)

    ax.set_xlabel("Er Photon Collection Efficiency")
    ax.set_ylabel("Microwave Efficiency")
    ax.set_title("Mw-Yb-Er Entanglement Rate")

    ax.set_xticks(np.arange(-0.5, len(EFFICIENCIES), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(EFFICIENCIES), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)

    if annotate:
        for row in range(grid.shape[0]):
            for col in range(grid.shape[1]):
                if not np.isnan(grid[row, col]):
                    ax.text(
                        col,
                        row,
                        f"{grid[row, col]:.2f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                    )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Rate (Hz)")

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    grid = load_rate_grid(args.data_dir)

    missing = np.argwhere(np.isnan(grid))
    if len(missing) > 0:
        print(f"Warning: {len(missing)} grid cells are missing entanglement-time data.")

    plot_heatmap(grid, args.output, args.annotate)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
