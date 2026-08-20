"""Run sweep experiments in parallel."""

import json
import os
import sys
import time
from pathlib import Path
from subprocess import PIPE, Popen
#NOTE  based off Caitao's runner he forwarded me. 

PARALLEL = 9 #went down to 9 but believe 10 would still be fine


# COMMAND = ["python3", "main_rb_rb_rb_EG_sim.py"]

COMMAND = [sys.executable, "main_simulations/main_het_net_four_node_sim.py"]
TWONODE_COMMAND = [sys.executable, "main_simulations/main_twonode.py"]
UW_YB_ER_COMMAND = [sys.executable, "main_simulations/main_uW_yb_er_MAIN.py"]
UW_RB_ER_COMMAND = [sys.executable, "main_simulations/main_uW_rb_er_MAIN.py"]
HET_TELEPORT_COMMAND = [sys.executable, "main_simulations/main_het_teleport_mw_rb_yb_rb_er.py"]
NUM_TRIALS = 1000 # four-node heterogeneous chain is much heavier than Rb-Rb-Rb
TWONODE_NUM_TRIALS = 12000
HET_FOUR_NODE_NUM_TRIALS = 200
UW_YB_ER_GRID_NUM_TRIALS = 3000
UW_RB_ER_GRID_NUM_TRIALS = 3000
UW_RB_ER_OPTIMISTIC_GRID_NUM_TRIALS = 1002
UW_RB_ER_EFFICIENCY_GRID_NUM_TRIALS = 1002
HET_TELEPORT_YB_VARIED_CHAIN_NUM_TRIALS = 3000 #set to 500 and run 20 times Vary seed
HET_TELEPORT_7YB_SPLIT_NUM_TRIALS = 500
HET_TELEPORT_7YB_SPLIT_RUNS = 20
HET_TELEPORT_7YB_BASE_SEED = 7000

COOLING_TIMES_PS = [100_000_000, 500_000_000, 1_000_000_000, 2_000_000_000, 3_000_000_000, 4_000_000_000, 5_000_000_000,]
PHOTON_COLLECTION_EFFICIENCIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
DETECTOR_EFFICIENCIES = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

TRANSMON_COHERENCE_TIMES_PS = [500_000_000, 1_000_000_000, 2_000_000_000, 4_000_000_000, 6_000_000_000, 8_000_000_000, 10_000_000_000,]

UW_YB_ER_GRID_OUTPUT_ROOT = Path("tmp_uW_Yb_Er_grid")
UW_YB_ER_GRID_OPTIMISTIC_OUTPUT_ROOT = Path("tmp_mw_yb_er_grid_optimistic")
UW_YB_ER_EFFICIENCY_GRID_OUTPUT_ROOT = Path("tmp_mw_yb_er_efficiency_grid")
UW_RB_ER_GRID_OUTPUT_ROOT = Path("tmp_mw_rb_er_grid")
UW_RB_ER_GRID_OPTIMISTIC_OUTPUT_ROOT = Path("tmp_mw_rb_er_grid_optimistic")
UW_RB_ER_EFFICIENCY_GRID_OUTPUT_ROOT = Path("tmp_mw_rb_er_efficiency_grid")
HET_TELEPORT_YB_VARIED_CHAIN_OUTPUT_ROOT = Path("tmp_teleport_yb_varied_chain")
HET_TELEPORT_7YB_SPLIT_OUTPUT_ROOT = Path("tmp_teleport_7yb_split")
UW_YB_ER_GRID_TRANSMON_COHERENCE_MS = [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
UW_YB_ER_GRID_ER_COHERENCE_MS = [0.2, 0.5, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
UW_YB_ER_GRID_EFFICIENCIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

ER_COMMAND = [sys.executable, "main_simulations/main_er_er_EG_sim.py"]
ER_OUTPUT_ROOT = Path("tmpErEr")
ER_OUTPUT_ROOT_5000 = Path("tmpErEr_5000")
ER_OUTPUT_ROOT_5000_DISTANCE_RUN2 = Path("tmpErEr_5000_distance_run2")
ER_OUTPUT_ROOT_DARK_COUNT_ZERO = Path("tmpErEr_dark_count_0")
ER_BASE_CONFIG = Path("config/linearErEr.json")
ER_RERUN_NUM_TRIALS = 5000
ER_DARK_COUNT_ZERO_NUM_TRIALS = 1000

ER_COHERENCE_TIMES_MS = [0.2, 0.5, 1, 2, 5, 10, 20]
ER_PHOTON_COLLECTION_EFFICIENCIES = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
ER_DISTANCES = [100, 200, 500, 1000, 2000, 5000, 10000]

TWONODE_PAIRS = [("yb", "yb"), ("yb", "rb"), ("yb", "er"), ("yb", "uw"), ("rb", "rb"), ("rb", "er"), ("rb", "uw"), ("er", "er"), ("er", "uw"), ("uw", "uw"),]

HET_TELEPORT_YB_VARIED_CHAIN_CONFIGS = {
    0: Path("config/teleport_mw_rb_rb_er.json"),
    1: Path("config/teleport_mw_rb_yb_rb_er.json"),
    2: Path("config/teleport_mw_rb_2yb_rb_er.json"),
    3: Path("config/teleport_mw_rb_3yb_rb_er.json"),
    4: Path("config/teleport_mw_rb_4yb_rb_er.json"),
    5: Path("config/teleport_mw_rb_5yb_rb_er.json"),
    6: Path("config/teleport_mw_rb_6yb_rb_er.json"),
}

LOADING_10_US_PS = 10_000_000
LOADING_300_MS_PS = 300_000_000_000


def add_num_trials(args: list[str]) -> list[str]:
    return args + ["-n", str(NUM_TRIALS)]


def add_er_num_trials(args: list[str], num_trials: int) -> list[str]:
    return args + ["-n", str(num_trials)]


def set_loading_time(args: list[str], loading_time: int) -> list[str]:
    return args + ["-load", str(loading_time)]


def set_cooling_time(args: list[str], cooling_time: int) -> list[str]:
    return args + ["-cool", str(cooling_time)]


def set_photon_collection_efficiency(args: list[str], pce: float) -> list[str]:
    return args + ["-pce", str(pce)]


def set_detector_efficiency(args: list[str], detector_efficiency: float) -> list[str]:
    return args + ["-dtctor_eff", str(detector_efficiency)]


def set_transmon_coherence(args: list[str], coherence_time: int) -> list[str]:
    return args + ["-uw_coherence", str(coherence_time)]


def set_log_file(args: list[str], log_file: str) -> list[str]:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    return args + ["-log", log_file]


def get_output(p: Popen):
    stderr = p.stderr.readlines()
    if stderr:
        for line in stderr:
            print(line.decode().rstrip())

    stdout = p.stdout.readlines()
    if stdout:
        for line in stdout:
            print(line.decode().rstrip())


def run_tasks(tasks: list[list[str]], parallel: int = PARALLEL): #makes Queue of our commands and starts new jobs while fewer than 9 running
    ps = []
    while len(tasks) > 0 or len(ps) > 0:
        if len(ps) < parallel and len(tasks) > 0:
            task = tasks.pop(0)
            print(task, f"{len(tasks)} still in queue")
            ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
        else:
            time.sleep(0.05)

        new_ps = []
        for p in ps:
            if p.poll() is None:
                new_ps.append(p)
            else:
                get_output(p)
        ps = new_ps


def base_args(loading_time: int) -> list[str]:
    args = []
    args = add_num_trials(args)
    args = set_loading_time(args, loading_time)
    return args


def build_cooling_time_tasks(data_dir: str, loading_time: int) -> list[list[str]]:
    tasks = []
    for cooling_time in COOLING_TIMES_PS:
        args = base_args(loading_time)
        args = set_cooling_time(args, cooling_time)
        args = set_log_file(
            args,
            f"{data_dir}/rb_cooling_time/cooling_time={cooling_time}.log",
        )
        tasks.append(COMMAND + args)
    return tasks


def build_photon_collection_efficiency_tasks(data_dir: str, loading_time: int) -> list[list[str]]:
    tasks = []
    for pce in PHOTON_COLLECTION_EFFICIENCIES:
        args = base_args(loading_time)
        args = set_photon_collection_efficiency(args, pce)
        args = set_log_file(args, f"{data_dir}/rb_pce/pce={pce}.log")
        tasks.append(COMMAND + args)
    return tasks


def build_detector_efficiency_tasks(data_dir: str, loading_time: int) -> list[list[str]]:
    tasks = []
    for detector_efficiency in DETECTOR_EFFICIENCIES:
        args = base_args(loading_time)
        args = set_detector_efficiency(args, detector_efficiency)
        args = set_log_file(
            args,
            f"{data_dir}/rb_detector_eff/detector_eff={detector_efficiency:.2f}.log",
        )
        tasks.append(COMMAND + args)
    return tasks


def build_rb_rb_rb_sweep_tasks(data_dir: str, loading_time: int) -> list[list[str]]:
    tasks = []
    tasks.extend(build_cooling_time_tasks(data_dir, loading_time))
    tasks.extend(build_photon_collection_efficiency_tasks(data_dir, loading_time))
    tasks.extend(build_detector_efficiency_tasks(data_dir, loading_time))
    return tasks


def main_rb_rb_rb_sweeps():
    tasks = []
    tasks.extend(build_rb_rb_rb_sweep_tasks("tmpRb3_run5", LOADING_10_US_PS))
    tasks.extend(build_rb_rb_rb_sweep_tasks("tmpRb3_300ms_run5", LOADING_300_MS_PS))
    run_tasks(tasks, parallel=PARALLEL)


def build_het_four_node_coherence_tasks(data_dir: str) -> list[list[str]]:
    tasks = []
    for coherence_time in TRANSMON_COHERENCE_TIMES_PS:
        coherence_ms = coherence_time * 1e-9
        args = []
        args = add_num_trials(args)
        args = set_transmon_coherence(args, coherence_time)
        args = set_log_file(
            args,
            f"{data_dir}/uw_coherence/coherence_ms={coherence_ms:g}.log",
        )
        tasks.append(COMMAND + args)
    return tasks


def main_het_four_node_coherence_sweep():
    tasks = build_het_four_node_coherence_tasks("tmpHet4")
    run_tasks(tasks, parallel=PARALLEL)


def build_het_four_node_default_optimistic_tasks(data_dir: str) -> list[list[str]]:
    tasks = []
    for label in ["default", "optimistic"]:
        for coherence_time in TRANSMON_COHERENCE_TIMES_PS:
            coherence_ms = coherence_time * 1e-9
            args = ["-n", str(HET_FOUR_NODE_NUM_TRIALS)]
            args = set_transmon_coherence(args, coherence_time)
            if label == "optimistic":
                args += [
                    "-pce", "1.0",
                    "-dtctor_eff", "1.0",
                    "-dtctor_dc", "0.0",
                    "-qfc_eff", "1.0",
                    "-qfc_noise", "0.0",
                    "-uw_efficiency", "1.0",
                    "-uw_noise", "0.0",
                    "-eta1", "1.0",
                    "-eta2", "1.0",
                    "-converter_noise", "0.0",
                    "-image_loss", "0.0",
                ]
            args = set_log_file(
                args,
                f"{data_dir}/{label}/uw_coherence/coherence_ms={coherence_ms:g}.log",
            )
            tasks.append(COMMAND + args)
    return tasks


def main_het_four_node_default_optimistic_sweep():
    tasks = build_het_four_node_default_optimistic_tasks("tmpHet4_default_optimistic")
    run_tasks(tasks, parallel=PARALLEL)


def build_het_four_node_optimistic_tasks(data_dir: str) -> list[list[str]]:
    tasks = []
    for coherence_time in TRANSMON_COHERENCE_TIMES_PS:
        coherence_ms = coherence_time * 1e-9
        args = ["-n", str(HET_FOUR_NODE_NUM_TRIALS)]
        args = set_transmon_coherence(args, coherence_time)
        args += ["-pce", "1.0", "-dtctor_eff", "1.0", "-dtctor_dc", "0.0", "-qfc_eff", "1.0", "-qfc_noise", "0.0", "-uw_efficiency", "1.0", "-uw_noise", "0.0", "-eta1", "1.0", "-eta2", "1.0", "-converter_noise", "0.0", "-image_loss", "0.0",]
        args = set_log_file(
            args,
            f"{data_dir}/uw_coherence/coherence_ms={coherence_ms:g}.log",
        )
        tasks.append(COMMAND + args)
    return tasks


def main_het_four_node_optimistic_sweep():
    tasks = build_het_four_node_optimistic_tasks("tmp/tmpHet4_optimistic")
    run_tasks(tasks, parallel=PARALLEL)


def er_ms_to_ps(milliseconds: float) -> int:
    return int(milliseconds * 1_000_000_000)


def build_uW_yb_er_coherence_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_coherence_ms in UW_YB_ER_GRID_TRANSMON_COHERENCE_MS:
        for er_coherence_ms in UW_YB_ER_GRID_ER_COHERENCE_MS:
            args = ["-n", str(UW_YB_ER_GRID_NUM_TRIALS)]
            args += ["-uw_coherence", str(er_ms_to_ps(uw_coherence_ms))]
            args += ["-er_coh", str(er_ms_to_ps(er_coherence_ms))]
            args = set_log_file(
                args,
                str(
                    UW_YB_ER_GRID_OUTPUT_ROOT
                    / "coherence_grid"
                    / f"uw_ms={uw_coherence_ms:g}_er_ms={er_coherence_ms:g}.log"
                ),
            )
            tasks.append(UW_YB_ER_COMMAND + args)
    return tasks


def main_uW_yb_er_coherence_grid():
    tasks = build_uW_yb_er_coherence_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_uW_yb_er_optimistic_coherence_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_coherence_ms in UW_YB_ER_GRID_TRANSMON_COHERENCE_MS:
        for er_coherence_ms in UW_YB_ER_GRID_ER_COHERENCE_MS:
            args = ["-n", str(UW_YB_ER_GRID_NUM_TRIALS),  "-uw_coherence", str(er_ms_to_ps(uw_coherence_ms)),  "-er_coh", str(er_ms_to_ps(er_coherence_ms)), "-yb_pce", "1.0", "-er_pce", "1.0", "-qfc_eff", "1.0", "-qfc_noise", "0.0", "-dtctor_eff", "1.0", "-uw_efficiency", "1.0", "-uw_noise", "0.0",]
            # Detector dark counts are default for now
            args = set_log_file(
                args,
                str(
                    UW_YB_ER_GRID_OPTIMISTIC_OUTPUT_ROOT
                    / "coherence_grid"
                    / f"uw_ms={uw_coherence_ms:g}_er_ms={er_coherence_ms:g}.log"
                ),
            )
            tasks.append(UW_YB_ER_COMMAND + args)
    return tasks


def main_uW_yb_er_optimistic_coherence_grid():
    tasks = build_uW_yb_er_optimistic_coherence_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_uW_yb_er_efficiency_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_efficiency in UW_YB_ER_GRID_EFFICIENCIES:
        for er_pce in UW_YB_ER_GRID_EFFICIENCIES:
            args = [
                "-n", str(UW_YB_ER_GRID_NUM_TRIALS),
                "-uw_efficiency", str(uw_efficiency),
                "-er_pce", str(er_pce),
            ]
            # Coherence-time arguments are omitted to use the simulation defaults.
            args = set_log_file(
                args,
                str(
                    UW_YB_ER_EFFICIENCY_GRID_OUTPUT_ROOT
                    / "efficiency_grid"
                    / f"uw_eff={uw_efficiency:g}_er_pce={er_pce:g}.log"
                ),
            )
            tasks.append(UW_YB_ER_COMMAND + args)
    return tasks


def main_uW_yb_er_efficiency_grid():
    tasks = build_uW_yb_er_efficiency_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_uW_rb_er_coherence_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_coherence_ms in UW_YB_ER_GRID_TRANSMON_COHERENCE_MS:
        for er_coherence_ms in UW_YB_ER_GRID_ER_COHERENCE_MS:
            args = ["-n", str(UW_RB_ER_GRID_NUM_TRIALS)]
            args += ["-uw_coherence", str(er_ms_to_ps(uw_coherence_ms))]
            args += ["-er_coh", str(er_ms_to_ps(er_coherence_ms))]
            args = set_log_file(
                args,
                str(
                    UW_RB_ER_GRID_OUTPUT_ROOT
                    / "coherence_grid"
                    / f"uw_ms={uw_coherence_ms:g}_er_ms={er_coherence_ms:g}.log"
                ),
            )
            tasks.append(UW_RB_ER_COMMAND + args)
    return tasks


def main_uW_rb_er_coherence_grid():
    tasks = build_uW_rb_er_coherence_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_uW_rb_er_optimistic_coherence_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_coherence_ms in UW_YB_ER_GRID_TRANSMON_COHERENCE_MS:
        for er_coherence_ms in UW_YB_ER_GRID_ER_COHERENCE_MS:
            args = ["-n", str(UW_RB_ER_OPTIMISTIC_GRID_NUM_TRIALS), "-uw_coherence", str(er_ms_to_ps(uw_coherence_ms)), "-er_coh", str(er_ms_to_ps(er_coherence_ms)), "-rb_pce", "1.0", "-er_pce", "1.0", "-eta1", "1.0", "-eta2", "1.0", "-converter_noise", "0.0", "-dtctor_eff", "1.0", "-uw_efficiency", "1.0", "-uw_noise", "0.0",]
            # Detector dark counts are default for now
            args = set_log_file(
                args,
                str(
                    UW_RB_ER_GRID_OPTIMISTIC_OUTPUT_ROOT
                    / "coherence_grid"
                    / f"uw_ms={uw_coherence_ms:g}_er_ms={er_coherence_ms:g}.log"
                ),
            )
            tasks.append(UW_RB_ER_COMMAND + args)
    return tasks


def main_uW_rb_er_optimistic_coherence_grid():
    tasks = build_uW_rb_er_optimistic_coherence_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_uW_rb_er_efficiency_grid_tasks() -> list[list[str]]:
    tasks = []
    for uw_efficiency in UW_YB_ER_GRID_EFFICIENCIES:
        for er_pce in UW_YB_ER_GRID_EFFICIENCIES:
            args = [
                "-n", str(UW_RB_ER_EFFICIENCY_GRID_NUM_TRIALS),
                "-uw_efficiency", str(uw_efficiency),
                "-er_pce", str(er_pce),
            ]
            # Coherence-time arguments are omitted to use the simulation defaults.
            args = set_log_file(
                args,
                str(
                    UW_RB_ER_EFFICIENCY_GRID_OUTPUT_ROOT
                    / "efficiency_grid"
                    / f"uw_eff={uw_efficiency:g}_er_pce={er_pce:g}.log"
                ),
            )
            tasks.append(UW_RB_ER_COMMAND + args)
    return tasks


def main_uW_rb_er_efficiency_grid():
    tasks = build_uW_rb_er_efficiency_grid_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_het_teleport_yb_varied_chain_tasks() -> list[list[str]]:
    tasks = []
    for number_of_yb_nodes, config_file in HET_TELEPORT_YB_VARIED_CHAIN_CONFIGS.items():
        args = [
            "-n", str(HET_TELEPORT_YB_VARIED_CHAIN_NUM_TRIALS),
            "-config", str(config_file),
        ]
        args = set_log_file(
            args,
            str(HET_TELEPORT_YB_VARIED_CHAIN_OUTPUT_ROOT / f"yb_nodes={number_of_yb_nodes}.log"),
        )
        tasks.append(HET_TELEPORT_COMMAND + args)
    return tasks


def main_het_teleport_yb_varied_chain():
    tasks = build_het_teleport_yb_varied_chain_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def build_het_teleport_7yb_split_tasks() -> list[list[str]]:
    tasks = []
    config_file = Path("config/teleport_mw_rb_7yb_rb_er.json")
    for run_index in range(HET_TELEPORT_7YB_SPLIT_RUNS):
        seed = HET_TELEPORT_7YB_BASE_SEED + run_index
        args = [
            "-n", str(HET_TELEPORT_7YB_SPLIT_NUM_TRIALS),
            "-config", str(config_file),
            "-seed", str(seed),
        ]
        args = set_log_file(
            args,
            str(HET_TELEPORT_7YB_SPLIT_OUTPUT_ROOT / f"run={run_index:02d}_seed={seed}.log"),
        )
        tasks.append(HET_TELEPORT_COMMAND + args)
    return tasks


def main_het_teleport_7yb_split():
    tasks = build_het_teleport_7yb_split_tasks()
    run_tasks(tasks, parallel=PARALLEL)


def make_er_distance_config(distance: int, output_root: Path = ER_OUTPUT_ROOT) -> Path:
    config_dir = output_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"linearErEr_distance={distance}.json"

    with ER_BASE_CONFIG.open("r") as infile:
        config = json.load(infile)

    if output_root == ER_OUTPUT_ROOT_5000_DISTANCE_RUN2:
        for node in config.get("nodes", []):
            node["seed"] = node.get("seed", 0) + 1000

    for qchannel in config.get("qchannels", []):
        qchannel["distance"] = float(distance)

    for cchannel in config.get("cchannels", []):
        cchannel["distance"] = float(distance)

    with config_file.open("w") as outfile:
        json.dump(config, outfile, indent=4)

    return config_file


def build_er_coherence_tasks() -> list[list[str]]:
    tasks = []
    for coherence_ms in ER_COHERENCE_TIMES_MS:
        args = []
        args = add_num_trials(args)
        args += ["-coh", str(er_ms_to_ps(coherence_ms))]
        args = set_log_file(
            args,
            str(ER_OUTPUT_ROOT / "er_coherence_time" / f"coherence_ms={coherence_ms:g}.log"),
        )
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_pce_tasks() -> list[list[str]]:
    tasks = []
    for pce in ER_PHOTON_COLLECTION_EFFICIENCIES:
        args = []
        args = add_num_trials(args)
        args += ["-pce", str(pce)]
        args = set_log_file(args, str(ER_OUTPUT_ROOT / "er_pce" / f"pce={pce:g}.log"))
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_pce_tasks_5000() -> list[list[str]]:
    tasks = []
    for pce in ER_PHOTON_COLLECTION_EFFICIENCIES:
        args = []
        args = add_er_num_trials(args, ER_RERUN_NUM_TRIALS)
        args += ["-pce", str(pce)]
        args = set_log_file(args, str(ER_OUTPUT_ROOT_5000 / "er_pce" / f"pce={pce:g}.log"))
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_distance_tasks(output_root: Path = ER_OUTPUT_ROOT, num_trials: int = NUM_TRIALS) -> list[list[str]]:
    tasks = []
    for distance in ER_DISTANCES:
        config_file = make_er_distance_config(distance, output_root)
        args = []
        args = add_er_num_trials(args, num_trials)
        args += ["-config", str(config_file)]
        args = set_log_file(args, str(output_root / "er_distance" / f"distance={distance}.log"))
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_distance_tasks_5000() -> list[list[str]]:
    return build_er_distance_tasks(ER_OUTPUT_ROOT_5000, ER_RERUN_NUM_TRIALS)


def build_er_distance_tasks_5000_run2() -> list[list[str]]:
    return build_er_distance_tasks(ER_OUTPUT_ROOT_5000_DISTANCE_RUN2, ER_RERUN_NUM_TRIALS)


def build_er_coherence_tasks_dark_count_zero() -> list[list[str]]:
    tasks = []
    for coherence_ms in ER_COHERENCE_TIMES_MS:
        args = []
        args = add_er_num_trials(args, ER_DARK_COUNT_ZERO_NUM_TRIALS)
        args += ["-dtctor_dc", "0"]
        args += ["-coh", str(er_ms_to_ps(coherence_ms))]
        args = set_log_file( args, str(ER_OUTPUT_ROOT_DARK_COUNT_ZERO / "er_coherence_time" / f"coherence_ms={coherence_ms:g}.log"),)
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_pce_tasks_dark_count_zero() -> list[list[str]]:
    tasks = []
    for pce in ER_PHOTON_COLLECTION_EFFICIENCIES:
        args = []
        args = add_er_num_trials(args, ER_DARK_COUNT_ZERO_NUM_TRIALS)
        args += ["-dtctor_dc", "0"]
        args += ["-pce", str(pce)]
        args = set_log_file(args, str(ER_OUTPUT_ROOT_DARK_COUNT_ZERO / "er_pce" / f"pce={pce:g}.log"))
        tasks.append(ER_COMMAND + args)
    return tasks


def build_er_distance_tasks_dark_count_zero() -> list[list[str]]:
    tasks = []
    for distance in ER_DISTANCES:
        config_file = make_er_distance_config(distance, ER_OUTPUT_ROOT_DARK_COUNT_ZERO)
        args = []
        args = add_er_num_trials(args, ER_DARK_COUNT_ZERO_NUM_TRIALS)
        args += ["-dtctor_dc", "0"]
        args += ["-config", str(config_file)]
        args = set_log_file(args, str(ER_OUTPUT_ROOT_DARK_COUNT_ZERO / "er_distance" / f"distance={distance}.log"))
        tasks.append(ER_COMMAND + args)
    return tasks


def main_er_er_sweeps():
    tasks = []
    tasks.extend(build_er_coherence_tasks())
    tasks.extend(build_er_pce_tasks())
    tasks.extend(build_er_distance_tasks())
    run_tasks(tasks, parallel=PARALLEL)


def main_er_er_pce_distance_5000_sweeps():
    tasks = []
    tasks.extend(build_er_pce_tasks_5000())
    tasks.extend(build_er_distance_tasks_5000())
    run_tasks(tasks, parallel=PARALLEL)


def main_er_er_dark_count_zero_sweeps():
    tasks = []
    tasks.extend(build_er_coherence_tasks_dark_count_zero())
    tasks.extend(build_er_pce_tasks_dark_count_zero())
    tasks.extend(build_er_distance_tasks_dark_count_zero())
    run_tasks(tasks, parallel=PARALLEL)


def main_er_er_distance_5000_run2_sweep():
    tasks = build_er_distance_tasks_5000_run2()
    run_tasks(tasks, parallel=PARALLEL)


def build_twonode_tasks() -> list[list[str]]:
    tasks = []
    for node1, node2 in TWONODE_PAIRS:
        args = [
            "-n1", node1,
            "-n2", node2,
            "-n", str(TWONODE_NUM_TRIALS),
        ]
        args = set_log_file(args, f"tmp/twonode_{node1}_{node2}.log")
        tasks.append(TWONODE_COMMAND + args)
    return tasks


def main_twonode_all_pairs():
    tasks = build_twonode_tasks()
    run_tasks(tasks, parallel=PARALLEL)


if __name__ == "__main__":
    # main_rb_rb_rb_sweeps()
    # main_het_four_node_coherence_sweep()
    # main_het_four_node_default_optimistic_sweep()
    # main_het_four_node_optimistic_sweep()
    # main_er_er_sweeps()
    # main_er_er_pce_distance_5000_sweeps()
    # main_er_er_dark_count_zero_sweeps()
    # main_er_er_distance_5000_run2_sweep()
    #main_twonode_all_pairs()
    #main_uW_yb_er_coherence_grid()
    #main_uW_yb_er_optimistic_coherence_grid()
    #main_uW_yb_er_efficiency_grid()
    #main_uW_rb_er_coherence_grid()
    #main_uW_rb_er_optimistic_coherence_grid()
    #main_uW_rb_er_efficiency_grid()
    #main_het_teleport_yb_varied_chain()
    main_het_teleport_7yb_split()
