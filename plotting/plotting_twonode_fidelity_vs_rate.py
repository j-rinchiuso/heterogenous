from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter

from plotting_twonode import LABELS, MEMORIES, log_path, parse_log


OUTPUT_FILE = Path("tmp/twonode_fidelity_vs_rate.png")

LABEL_OFFSETS = {
    ("yb", "yb"): (8, -2),
    ("yb", "rb"): (8, 8),
    ("yb", "er"): (8, 8),
    ("yb", "uw"): (8, -14),
    ("rb", "rb"): (8, -14),
    ("rb", "er"): (8, 8),
    ("rb", "uw"): (-8, 8),
    ("er", "er"): (8, 8),
    ("er", "uw"): (-8, -14),
    ("uw", "uw"): (-8, 8),}


def pair_label(first_memory: str, second_memory: str) -> str:
    return f"{LABELS[first_memory]}–{LABELS[second_memory]}"


def make_plot() -> None:
    figure, axis = plt.subplots(figsize=(9, 6))

    for first_index, first_memory in enumerate(MEMORIES):
        for second_memory in MEMORIES[first_index:]:
            fidelity, rate = parse_log(log_path(first_memory, second_memory))
            axis.scatter(rate, fidelity, color="#17697f", edgecolor="black", s=85, zorder=3)

            x_offset, y_offset = LABEL_OFFSETS[(first_memory, second_memory)]
            axis.annotate(
                pair_label(first_memory, second_memory),
                (rate, fidelity), xytext=(x_offset, y_offset), textcoords="offset points", fontsize=11, ha="right" if x_offset < 0 else "left", va="top" if y_offset < 0 else "bottom",)
    axis.set_xscale("log")
    axis.set_xlim(0.1, 100)
    axis.xaxis.set_major_locator(FixedLocator([0.1, 1, 10, 100]))
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{value:g}"))
    axis.set_xlabel("Entanglement Rate (Hz)")
    axis.set_ylabel("Fidelity")
    axis.set_ylim(0.55, 1.01)
    axis.grid(True, which="major", alpha=0.35)
    axis.set_title("Two-Node Entanglement Fidelity vs. Rate")
    figure.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.close(figure)

if __name__ == "__main__":
    make_plot()
    print(f"Saved {OUTPUT_FILE}")
