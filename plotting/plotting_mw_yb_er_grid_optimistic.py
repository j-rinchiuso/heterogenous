"""Plot the optimistic microwave-Yb-Er coherence-grid precise fidelity."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


MW_MS = [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
ER_MS = [0.2, 0.5, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

DEFAULT_DATA_DIR = Path("tmp_mw_yb_er_grid_optimistic/coherence_grid")
DEFAULT_OUTPUT = Path("tmp/mw_yb_er_optimistic_fidelity_heatmap.png")

PRECISE_FIDELITY_PATTERN = re.compile(
    r"calculated precise fidelity\s*=\s*([-+0-9.eE]+)"
)
LOG_NAME_RE = re.compile(r"[uU][wW]_ms=([0-9.]+)_er_ms=([0-9.]+)\.log$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot the optimistic microwave-Yb-Er precise-fidelity grid."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing uw_ms=..._er_ms=....log files.",
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
        help="Write the precise fidelity value inside each heatmap cell.",
    )
    return parser.parse_args()


def read_precise_fidelity(log_file: Path) -> float:
    value = None
    for line in log_file.read_text(errors="ignore").splitlines():
        match = PRECISE_FIDELITY_PATTERN.search(line)
        if match:
            value = float(match.group(1))
    if value is None:
        raise ValueError(f"Could not find precise fidelity in {log_file}")
    return value


def load_grid(data_dir: Path) -> np.ndarray:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Optimistic grid directory not found: {data_dir}")

    grid = np.full((len(MW_MS), len(ER_MS)), np.nan)
    mw_index = {value: index for index, value in enumerate(MW_MS)}
    er_index = {value: index for index, value in enumerate(ER_MS)}

    for log_file in data_dir.glob("*.log"):
        match = LOG_NAME_RE.fullmatch(log_file.name)
        if not match:
            continue

        mw_ms = float(match.group(1))
        er_ms = float(match.group(2))
        if mw_ms not in mw_index or er_ms not in er_index:
            continue

        grid[mw_index[mw_ms], er_index[er_ms]] = read_precise_fidelity(log_file)

    return grid


def plot_heatmap(grid: np.ndarray, output: Path, annotate: bool) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    masked_grid = np.ma.masked_invalid(grid)

    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad(color="#eeeeee")
    image = ax.imshow(
        masked_grid,
        cmap=cmap,
        vmin=0,
        vmax=1.0,
        aspect="auto",
        origin="lower",
    )

    ax.set_xticks(np.arange(len(ER_MS)))
    ax.set_xticklabels([str(value) for value in ER_MS])
    ax.set_yticks(np.arange(len(MW_MS)))
    ax.set_yticklabels([str(value) for value in MW_MS])
    ax.set_xlabel("Erbium Coherence Time (ms)")
    ax.set_ylabel("Microwave Coherence Time (ms)")
    ax.set_title("Optimistic uW-Yb-Er Fidelity")

    ax.set_xticks(np.arange(-0.5, len(ER_MS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(MW_MS), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)

    if annotate:
        for row in range(grid.shape[0]):
            for col in range(grid.shape[1]):
                if not np.isnan(grid[row, col]):
                    ax.text(
                        col,
                        row,
                        f"{grid[row, col]:.3f}",
                        ha="center",
                        va="center",
                        fontsize=7,
                    )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Precise Fidelity")

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    grid = load_grid(args.data_dir)

    missing = np.argwhere(np.isnan(grid))
    if len(missing) > 0:
        print(f"Warning: {len(missing)} grid cells are missing precise fidelity data.")

    plot_heatmap(grid, args.output, args.annotate)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
