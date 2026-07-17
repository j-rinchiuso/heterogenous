import glob
import re

import matplotlib.pyplot as plt
import numpy as np


DATA_DIR = "tmp/tmpHet4/uw_coherence"
OUTPUT_FILE = "tmp/het_four_node_coherence.png"
COHERENCE_TICKS = [0.5, 1, 2, 4, 6, 8, 10]
COHERENCE_TICK_LABELS = ["0.5", "1.0", "2.0", "4.0", "6.0", "8.0", "10.0"]


def parse_log(filename):
    data = {}
    with open(filename, "r") as f:
        for line in f:
            if "calculated fidelity=" in line:
                value = line.rsplit("calculated fidelity=", 1)[1].strip()
                data["fidelity"] = None if value == "None" else float(value)
            elif "Average four-node end-to-end entanglement time is ~" in line:
                avg_time = float(line.rsplit("~", 1)[1].strip())
                data["rate"] = 1 / avg_time

    if "rate" not in data:
        raise ValueError(f"Missing average entanglement time in {filename}")
    if "fidelity" not in data:
        raise ValueError(f"Missing fidelity in {filename}")
    return data


def coherence_from_filename(filename):
    match = re.search(r"coherence_ms=([0-9.]+)\.log", filename)
    if not match:
        raise ValueError(f"Could not parse coherence value from {filename}")
    return float(match.group(1))


def collect_points():
    points = []
    for filename in glob.glob(f"{DATA_DIR}/coherence_ms=*.log"):
        data = parse_log(filename)
        if data["fidelity"] is None:
            continue
        points.append((coherence_from_filename(filename), data["rate"], data["fidelity"]))
    return sorted(points)


def make_plot(output_file=OUTPUT_FILE):
    points = collect_points()
    if not points:
        raise ValueError(f"No complete data found in {DATA_DIR}")

    coherence = [point[0] for point in points]
    rates = [point[1] for point in points]
    fidelities = [point[2] for point in points]

    x_positions = np.arange(len(coherence))

    plt.rcParams["font.size"] = 14
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    fig.subplots_adjust(left=0.07, right=0.99, top=0.95, bottom=0.24, wspace=0.27)

    axes[0].plot(x_positions, rates, color="red", marker="^", markersize=6, label="Default")
    axes[0].set_xlabel("Transmon T1 Coherence Time (ms)\n(a)")
    axes[0].set_ylabel("Rate (Hz)")
    axes[0].set_ylim(0, 12)
    axes[0].set_xticks(x_positions)
    axes[0].set_xticklabels(COHERENCE_TICK_LABELS)
    axes[0].set_yticks([0, 2, 4, 6, 8, 10, 12])
    axes[0].grid(True)
    axes[0].legend(loc="upper left")

    axes[1].plot(x_positions, fidelities, color="red", marker="^", markersize=6, label="Default")
    axes[1].set_xlabel("Transmon T1 Coherence Time (ms)\n(b)")
    axes[1].set_ylabel("Fidelity")
    axes[1].set_ylim(-0.2, 0.8)
    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(COHERENCE_TICK_LABELS)
    axes[1].set_yticks([-0.2, 0.0, 0.2, 0.4, 0.6, 0.8])
    axes[1].grid(True)
    axes[1].legend(loc="upper left")

    plt.savefig(output_file)
    plt.close(fig)


if __name__ == "__main__":
    make_plot()
