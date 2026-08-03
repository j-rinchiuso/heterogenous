import re
from pathlib import Path

import matplotlib.pyplot as plt


MEMORIES = ["yb", "rb", "er", "uw"]
LABELS = {
    "yb": "Yb",
    "rb": "Rb",
    "er": r"$Er^{3+}$",
    "uw": r"$\mu W$",
}

LOG_DIR = Path("tmp")
OUTPUT_FILE = Path("tmp/twonode_summary_table_preciseFidelity.png")


def log_path(node1, node2):
    first = LOG_DIR / f"twonode_{node1}_{node2}.log"
    if first.exists():
        return first

    second = LOG_DIR / f"twonode_{node2}_{node1}.log"
    if second.exists():
        return second

    raise FileNotFoundError(f"Missing log for {node1}-{node2}")


def parse_log(filename):
    fidelity = None
    default_fidelity = None
    avg_time = None

    with open(filename, "r") as f:
        for line in f:
            if "calculated precise fidelity =" in line:
                fidelity = float(line.rsplit("=", 1)[1].strip())
            elif "calculated fidelity =" in line and "best estimate" not in line:
                default_fidelity = float(line.rsplit("=", 1)[1].strip())
            elif "Average ent time is ~" in line:
                avg_time = float(line.rsplit("~", 1)[1].strip())

    if fidelity is None:
        fidelity = default_fidelity

    if fidelity is None or avg_time is None:
        raise ValueError(f"Missing fidelity or average time in {filename}")

    return fidelity, 1 / avg_time


def build_table_data():
    rows = []

    for row_index, row_memory in enumerate(MEMORIES):
        row = [LABELS[row_memory]]
        for col_index, col_memory in enumerate(MEMORIES):
            if col_index < row_index:
                row.append("")
                continue

            fidelity, rate = parse_log(log_path(row_memory, col_memory))
            row.append(f"Fidelity: {fidelity:.4f}\nRate: {rate:.4f} Hz")
        rows.append(row)

    return rows


def make_plot():
    table_data = build_table_data()
    columns = [""] + [LABELS[memory] for memory in MEMORIES]

    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.axis("off")

    table = ax.table(
        cellText=table_data,
        colLabels=columns,
        cellLoc="left",
        loc="center",
        bbox=[0, 0, 1, 1],
    )

    header_color = "#17697f"
    stripe_color = "#e7e7e7"

    table.auto_set_font_size(False)
    table.set_fontsize(14)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("black")
        cell.set_linewidth(0.8)

        if row == 0 or col == 0:
            cell.set_facecolor(header_color)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
            cell.get_text().set_ha("center")
            cell.get_text().set_va("center")
        else:
            cell.set_facecolor(stripe_color if row % 2 == 1 else "white")
            cell.get_text().set_ha("left")
            cell.get_text().set_va("center")

    for row in range(len(MEMORIES) + 1):
        table[(row, 0)].set_width(0.2)
        for col in range(1, len(MEMORIES) + 1):
            table[(row, col)].set_width(0.2)

    for col in range(len(MEMORIES) + 1):
        table[(0, col)].set_height(0.19)
    for row in range(1, len(MEMORIES) + 1):
        for col in range(len(MEMORIES) + 1):
            table[(row, col)].set_height(0.19)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    make_plot()
    print(f"Saved {OUTPUT_FILE}")
