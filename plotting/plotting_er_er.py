import glob
import re
from pathlib import Path

import matplotlib.pyplot as plt


ER_DATA_DIR = Path("tmpErEr")
COHERENCE_DATA_DIR = ER_DATA_DIR
PCE_DISTANCE_DATA_DIR = ER_DATA_DIR
DISTANCE_DATA_DIRS = [ER_DATA_DIR]
DISTANCE_DATA_DIR_RUN2 = Path("tmpErEr_5000_distance_run2")
DARK_COUNT_ZERO_DATA_DIR = Path("tmpErEr_dark_count_0")
OUTPUT_FILE = Path("tmp/er_er_sweeps.png")
OUTPUT_FILE_DARK_COUNT_ZERO = Path("tmp/er_er_sweeps_dark_count_0.png")

COHERENCE_TIMES_MS = [0.2, 0.5, 1, 2, 5, 10, 20]
PHOTON_COLLECTION_EFFICIENCIES = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
DISTANCES = [100, 200, 500, 1000, 2000, 5000, 10000]


def parse_log(filename):
    data = {}
    with open(filename, "r") as infile:
        for line in infile:
            if "successful entanglement attempts" in line:
                match = re.search(r"After ([0-9]+) successful", line)
                if match is not None:
                    data["num_trials"] = int(match.group(1))
            if "calculated fidelity =" in line:
                data["fidelity"] = float(line.rsplit("=", 1)[1].strip())
            elif "Average ent time is ~" in line:
                avg_time = float(line.rsplit("~", 1)[1].strip())
                data["avg_time"] = avg_time
                data["rate"] = 1 / avg_time

    if "fidelity" not in data or "rate" not in data:
        raise ValueError(f"Missing fidelity/rate summary in {filename}")
    if "num_trials" not in data:
        data["num_trials"] = 1

    return data


def value_from_filename(filename, pattern):
    match = re.search(pattern, filename)
    if match is None:
        raise ValueError(f"Could not parse x-axis value from {filename}")
    return float(match.group(1))


def collect_series(data_dir, subdir, file_glob, filename_pattern):
    points = []
    for filename in glob.glob(str(data_dir / subdir / file_glob)):
        data = parse_log(filename)
        x = value_from_filename(filename, filename_pattern)
        points.append((x, data["fidelity"], data["rate"]))
    return sorted(points)


def collect_expected_series(data_dir, subdir, values, filename_template):
    points = []
    for value in values:
        filename = data_dir / subdir / filename_template.format(value=value)
        if not filename.exists():
            raise FileNotFoundError(f"Missing expected sweep log: {filename}")
        data = parse_log(filename)
        points.append((value, data["fidelity"], data["rate"]))
    return points


def collect_combined_expected_series(data_dirs, subdir, values, filename_template):
    points = []
    for value in values:
        logs = []
        for data_dir in data_dirs:
            filename = data_dir / subdir / filename_template.format(value=value)
            if not filename.exists():
                raise FileNotFoundError(f"Missing expected sweep log: {filename}")
            logs.append(parse_log(filename))

        total_trials = sum(log["num_trials"] for log in logs)
        fidelity = sum(log["fidelity"] * log["num_trials"] for log in logs) / total_trials
        avg_time = sum(log["avg_time"] * log["num_trials"] for log in logs) / total_trials
        rate = 1 / avg_time
        points.append((value, fidelity, rate))
    return points


def plot_panel(ax, points, xlabel, ylim_fidelity=None):
    if not points:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_xlabel(xlabel)
        return

    x = [point[0] for point in points]
    fidelity = [point[1] for point in points]
    rate = [point[2] for point in points]

    ax.plot(x, fidelity, color="blue", marker="s", markersize=4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fidelity", color="blue")
    if ylim_fidelity is not None:
        ax.set_ylim(*ylim_fidelity)
    ax.tick_params(axis="y", colors="blue")
    ax.grid(True)

    ax_rate = ax.twinx()
    ax_rate.plot(x, rate, color="red", marker="^", markersize=4)
    ax_rate.set_ylabel("Rate (Hz)", color="red")
    ax_rate.tick_params(axis="y", colors="red")


def make_plot(coherence_data_dir, pce_data_dir, distance_data_dirs, output_file):
    coherence_points = collect_expected_series(
        coherence_data_dir,
        "er_coherence_time",
        COHERENCE_TIMES_MS,
        "coherence_ms={value:g}.log",
    )
    pce_points = collect_expected_series(
        pce_data_dir,
        "er_pce",
        PHOTON_COLLECTION_EFFICIENCIES,
        "pce={value:g}.log",
    )
    distance_points = collect_combined_expected_series(
        distance_data_dirs,
        "er_distance",
        DISTANCES,
        "distance={value:g}.log",
    )

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
    fig.subplots_adjust(left=0.06, right=0.94, top=0.95, bottom=0.22, wspace=0.5)

    plot_panel(axes[0], coherence_points, "Coherence Time (ms)\n(a)", ylim_fidelity=(0.5, 1.0))
    plot_panel(axes[1], pce_points, "Photon Collection Efficiency\n(b)", ylim_fidelity=(0.4, 1.0))
    #plot_panel(axes[2], distance_points, "Distance (m)\n(c)")
    plot_panel(axes[2], distance_points, "Distance (m)\n(c)", ylim_fidelity=(.8, 1.0))

    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    make_plot(
        COHERENCE_DATA_DIR,
        PCE_DISTANCE_DATA_DIR,
        DISTANCE_DATA_DIRS,
        OUTPUT_FILE,
    )
    # Dark-count-zero comparison run. Kept for later, but not active for the
    # standard Er-Er refresh.
    # make_plot(
    #     DARK_COUNT_ZERO_DATA_DIR,
    #     DARK_COUNT_ZERO_DATA_DIR,
    #     [DARK_COUNT_ZERO_DATA_DIR],
    #     OUTPUT_FILE_DARK_COUNT_ZERO,
    # )
