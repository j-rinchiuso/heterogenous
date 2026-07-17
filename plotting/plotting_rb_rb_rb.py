import glob
import re
from collections import defaultdict
from statistics import mean

import matplotlib.pyplot as plt

#very similar to old plotting file but change to Rb-Rb-Rb data 
def parse_log(filename):
    data = {}
    with open(filename, "r") as f:
        for line in f:
            if "pce:" in line:
                data["pce"] = float(line.rsplit("pce:", 1)[1].strip())
            elif "cooling_time_ms:" in line:
                data["cooling_time_ms"] = float(line.rsplit("cooling_time_ms:", 1)[1].strip())
            elif "calculated fidelity =" in line:
                data["fidelity"] = float(line.rsplit("=", 1)[1].strip())
            elif "Average swapped ent time is ~" in line:
                avg_time = float(line.rsplit("~", 1)[1].strip())
                data["rate"] = 1 / avg_time
            elif "Average ent time is ~" in line:
                avg_time = float(line.rsplit("~", 1)[1].strip())
                data["rate"] = 1 / avg_time
            elif "generation success rate:" in line:
                data["success_rate"] = float(line.rsplit("generation success rate:", 1)[1].strip())

    if "fidelity" not in data or "rate" not in data:
        raise ValueError(f"Missing fidelity/rate summary in {filename}")
    return data


def value_from_filename(filename, pattern):
    match = re.search(pattern, filename)
    if not match:
        raise ValueError(f"Could not parse x-axis value from {filename}")
    return float(match.group(1))


def collect_series(files, x_key=None, filename_pattern=None):
    points = []
    for filename in files:
        data = parse_log(filename)
        if x_key is not None:
            x = data[x_key]
        else:
            x = value_from_filename(filename, filename_pattern)
        points.append((x, data["fidelity"], data["rate"]))
    return sorted(points)


def collect_average_series(data_dirs, subdir, file_glob, x_key=None, filename_pattern=None):
    grouped_points = defaultdict(list)

    for data_dir in data_dirs:
        files = glob.glob(f"{data_dir}/{subdir}/{file_glob}")
        for filename in files:
            data = parse_log(filename)
            if x_key is not None:
                x = data[x_key]
            else:
                x = value_from_filename(filename, filename_pattern)
            grouped_points[x].append((data["fidelity"], data["rate"]))

    points = []
    for x, values in grouped_points.items():
        fidelity = mean(value[0] for value in values)
        rate = mean(value[1] for value in values)
        points.append((x, fidelity, rate))

    return sorted(points)


def plot_panel(ax, points, xlabel, ylim_fid=(0.9, 1.0), ylim_rate=None):
    x = [p[0] for p in points]
    fidelity = [p[1] for p in points]
    rate = [p[2] for p in points]

    ax.plot(x, fidelity, color="blue", marker="s", markersize=4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fidelity", color="blue")
    ax.set_ylim(*ylim_fid)
    ax.tick_params(axis="y", colors="blue")
    ax.grid(True)

    ax_rate = ax.twinx()
    ax_rate.plot(x, rate, color="red", marker="^", markersize=4)
    ax_rate.set_ylabel("Rate (Hz)", color="red")
    if ylim_rate is not None:
        ax_rate.set_ylim(*ylim_rate)
    ax_rate.tick_params(axis="y", colors="red")


def make_plot(data_dirs, output_filename):
    cooling_points = collect_average_series(
        data_dirs,
        "rb_cooling_time",
        "cooling_time=*.log",
        x_key="cooling_time_ms",
    )
    pce_points = collect_average_series(
        data_dirs,
        "rb_pce",
        "pce=*.log",
        filename_pattern=r"pce=([0-9.]+)\.log",
    )
    detector_points = collect_average_series(
        data_dirs,
        "rb_detector_eff",
        "detector_eff=*.log",
        filename_pattern=r"detector_eff=([0-9.]+)\.log",
    )

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
    fig.subplots_adjust(left=0.06, right=0.94, top=0.95, bottom=0.22, wspace=0.5)

    plot_panel(axes[0], cooling_points, "Cooling Time (ms)\n(a)", ylim_fid=(0.9, 1.0))
    plot_panel(axes[1], pce_points, "Photon Collection Efficiency\n(b)", ylim_fid=(0.6, 1.0))
    plot_panel(axes[2], detector_points, "Detector Efficiency\n(c)", ylim_fid=(0.9, 1.0))

    plt.savefig(output_filename, dpi=300)
    plt.close(fig)


make_plot(["tmpRb3", "tmpRb3_run2", "tmpRb3_run3", "tmpRb3_run4", "tmpRb3_run5"], "tmp/rb_rb_rb_sweeps_10microsec.png") #send to the tmp folder
make_plot(["tmpRb3_300ms", "tmpRb3_300ms_run2", "tmpRb3_300ms_run3", "tmpRb3_300ms_run4", "tmpRb3_300ms_run5"], "tmp/rb_rb_rb_sweeps_300ms.png")
