import re
from pathlib import Path

import matplotlib.pyplot as plt


DATA_DIRECTORY = Path("tmp_teleport_yb_varied_chain")
OUTPUT_FILE = DATA_DIRECTORY / "teleport_fidelity_latency_vs_yb_nodes.png"
NUMBER_OF_YB_NODES = list(range(7))

FIDELITY_PATTERN = re.compile(
    r"Teleport fidelity after Rb measurement, Mw measurement, and gate losses:\s*([0-9.]+)%"
)
LATENCY_PATTERN = re.compile(
    r"Average teleport latency:\s*([0-9.eE+-]+)\s*seconds"
)


def read_final_metrics(log_file: Path) -> tuple[float, float]:
    text = log_file.read_text(errors="replace")
    fidelity_matches = FIDELITY_PATTERN.findall(text)
    latency_matches = LATENCY_PATTERN.findall(text)
    if not fidelity_matches:
        raise ValueError(f"Final operation-adjusted teleport fidelity summary not found in {log_file}")
    if not latency_matches:
        raise ValueError(f"Final average latency summary not found in {log_file}")
    fidelity = float(fidelity_matches[-1]) / 100
    latency = float(latency_matches[-1])
    return fidelity, latency

def main() -> None:
    fidelities = []
    latencies = []
    for number_of_yb_nodes in NUMBER_OF_YB_NODES:
        log_file = DATA_DIRECTORY / f"yb_nodes={number_of_yb_nodes}.log"
        if not log_file.is_file():
            raise FileNotFoundError(f"Missing teleport result log: {log_file}")
        fidelity, latency = read_final_metrics(log_file)
        fidelities.append(fidelity)
        latencies.append(latency)
    figure, fidelity_axis = plt.subplots(figsize=(8, 5))
    latency_axis = fidelity_axis.twinx()
    fidelity_line = fidelity_axis.plot(NUMBER_OF_YB_NODES,fidelities, color="blue", marker="s", linewidth=2, markersize=6, label="Teleport Fidelity",)
    latency_line = latency_axis.plot( NUMBER_OF_YB_NODES, latencies, color="red", marker="^", linewidth=2, markersize=6, label="Average Latency",)
    fidelity_axis.set_xlabel("Number of Intermediate Yb Nodes")
    fidelity_axis.set_ylabel("Teleport Fidelity", color="blue")
    latency_axis.set_ylabel("Average Latency (s)", color="red")
    fidelity_axis.set_xticks(NUMBER_OF_YB_NODES)
    fidelity_axis.set_ylim(0, 1)
    latency_axis.set_ylim(bottom=0)
    fidelity_axis.tick_params(axis="y", colors="blue")
    latency_axis.tick_params(axis="y", colors="red")
    fidelity_axis.grid(True, alpha=0.5)
    lines = fidelity_line + latency_line
    fidelity_axis.legend(lines, [line.get_label() for line in lines], loc="best")
    fidelity_axis.set_title("Teleport Fidelity and Latency vs. Intermediate Yb Nodes")
    figure.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved plot to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
