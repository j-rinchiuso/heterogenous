import re
from pathlib import Path

import matplotlib.pyplot as plt


DATA_DIRECTORY = Path("tmp_teleport_yb_varied_chain")
DATA_DIRECTORY_7YB = Path("tmp_teleport_7yb_split")
OUTPUT_FILE = DATA_DIRECTORY / "teleport_fidelity_latency_vs_yb_nodes.png"
NUMBER_OF_YB_NODES = list(range(8))
OPERATION_FIDELITY_FACTOR = 0.996 * 0.992 * 0.95

TRIAL_RESULT_PATTERN = re.compile(
    r"Mw-to-Er teleportation trial \d+ (succeeded|failed) "
    r"\(completed=(True|False), direct match=(True|False), "
    r"latency=(None|[0-9.eE+-]+)(?: seconds)?\)"
)


def read_trial_totals(log_files: list[Path]) -> tuple[int, int, float, int]:
    successful_trials = 0
    recorded_trials = 0
    total_latency = 0.0
    completed_trials = 0

    for log_file in log_files:
        results = TRIAL_RESULT_PATTERN.findall(log_file.read_text(errors="replace"))
        recorded_trials += len(results)
        for result, completed, direct_match, latency in results:
            successful_trials += int(result == "succeeded" and direct_match == "True")
            if completed == "True" and latency != "None":
                total_latency += float(latency)
                completed_trials += 1

    if recorded_trials == 0:
        raise ValueError(f"No trial results found in {log_files}")
    if completed_trials == 0:
        raise ValueError(f"No completed teleport latencies found in {log_files}")
    return successful_trials, recorded_trials, total_latency, completed_trials


def log_files_for(number_of_yb_nodes: int) -> list[Path]:
    if number_of_yb_nodes in (5, 6):
        log_files = [DATA_DIRECTORY / f"recovered_yb_nodes_{number_of_yb_nodes}.log"]
    elif number_of_yb_nodes == 7:
        log_files = sorted(DATA_DIRECTORY_7YB.glob("run=*_seed=*.log"))
        if len(log_files) != 20:
            raise ValueError(f"Expected 20 seven-Yb logs, found {len(log_files)}")
    else:
        log_files = [DATA_DIRECTORY / f"yb_nodes={number_of_yb_nodes}.log"]

    missing_log_files = [log_file for log_file in log_files if not log_file.is_file()]
    if missing_log_files:
        raise FileNotFoundError(f"Missing teleport result logs: {missing_log_files}")
    return log_files

def main() -> None:
    fidelities = []
    latencies = []
    for number_of_yb_nodes in NUMBER_OF_YB_NODES:
        successful_trials, recorded_trials, total_latency, completed_trials = read_trial_totals(
            log_files_for(number_of_yb_nodes)
        )
        fidelity = successful_trials / recorded_trials * OPERATION_FIDELITY_FACTOR
        latency = total_latency / completed_trials
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
    fidelity_axis.legend(lines, [line.get_label() for line in lines], loc="lower right")
    fidelity_axis.set_title("Teleport Fidelity and Latency vs. Intermediate Yb Nodes")
    figure.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved plot to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
