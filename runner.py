"""Run Rb-Rb-Rb sweep experiments in parallel."""

import os
import time
from subprocess import PIPE, Popen
#NOTE heavily based off Caitao's runner he forwarded me. 

PARALLEL = 9 #went down to 9 but believe 10 would still be fine
COMMAND = ["python3", "main_rb_rb_rb_EG_sim.py"] #main command to run from our new Rb-Rb-Rb sim
NUM_TRIALS = 1000 #1000 may have been ambitious took very long 

COOLING_TIMES_PS = [
    100_000_000,
    500_000_000,
    1_000_000_000,
    2_000_000_000,
    3_000_000_000,
    4_000_000_000,
    5_000_000_000,
]
PHOTON_COLLECTION_EFFICIENCIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
DETECTOR_EFFICIENCIES = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

LOADING_10_US_PS = 10_000_000
LOADING_300_MS_PS = 300_000_000_000


def add_num_trials(args: list[str]) -> list[str]:
    return args + ["-n", str(NUM_TRIALS)]


def set_loading_time(args: list[str], loading_time: int) -> list[str]:
    return args + ["-load", str(loading_time)]


def set_cooling_time(args: list[str], cooling_time: int) -> list[str]:
    return args + ["-cool", str(cooling_time)]


def set_photon_collection_efficiency(args: list[str], pce: float) -> list[str]:
    return args + ["-pce", str(pce)]


def set_detector_efficiency(args: list[str], detector_efficiency: float) -> list[str]:
    return args + ["-dtctor_eff", str(detector_efficiency)]


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


if __name__ == "__main__":
    main_rb_rb_rb_sweeps()
