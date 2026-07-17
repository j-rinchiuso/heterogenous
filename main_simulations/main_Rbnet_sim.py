from __future__ import annotations

import argparse
import json
from pathlib import Path

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import HetRequestApp
from memory import MemoryArray
from yb_router_net_topo import YbRouterNetTopo


def build_rb_line_config(
    num_nodes: int,
    memo_size: int,
    distance: float,
    attenuation: float,
    seed_offset: int,
    classical_delay: int,
) -> dict:
    if num_nodes < 2:
        raise ValueError("Rb line simulation needs at least 2 router nodes.")

    config = {
        "templates": {
            "rb_rb_time_bin": {"encoding_type": "het_time_bin"},
            "Rb": {"memo_type": "Rb", "wavelength": "780"},
        },
        "nodes": [],
        "qchannels": [],
        "cchannels": [],
        "formalism": "ket_vector",
    }

    for i in range(num_nodes):
        config["nodes"].append(
            {
                "name": f"router_{i}",
                "type": "QuantumRouter",
                "seed": seed_offset + i,
                "memo_size": memo_size,
                "template": "Rb",
            }
        )

    for i in range(num_nodes - 1):
        config["nodes"].append(
            {
                "name": f"BSM_{i}_{i + 1}",
                "type": "BSMNode",
                "seed": seed_offset + num_nodes + i,
                "template": "rb_rb_time_bin",
            }
        )

        config["qchannels"].extend(
            [
                {
                    "source": f"router_{i}",
                    "destination": f"BSM_{i}_{i + 1}",
                    "distance": distance,
                    "attenuation": attenuation,
                },
                {
                    "source": f"router_{i + 1}",
                    "destination": f"BSM_{i}_{i + 1}",
                    "distance": distance,
                    "attenuation": attenuation,
                },
            ]
        )

        config["cchannels"].extend(
            [
                {
                    "source": f"BSM_{i}_{i + 1}",
                    "destination": f"router_{i}",
                    "distance": distance,
                },
                {
                    "source": f"router_{i}",
                    "destination": f"BSM_{i}_{i + 1}",
                    "distance": distance,
                },
                {
                    "source": f"BSM_{i}_{i + 1}",
                    "destination": f"router_{i + 1}",
                    "distance": distance,
                },
                {
                    "source": f"router_{i + 1}",
                    "destination": f"BSM_{i}_{i + 1}",
                    "distance": distance,
                },
            ]
        )

    for src in range(num_nodes):
        for dst in range(num_nodes):
            if src == dst:
                continue
            config["cchannels"].append(
                {
                    "source": f"router_{src}",
                    "destination": f"router_{dst}",
                    "delay": classical_delay,
                }
            )

    return config


def write_generated_config(config: dict, num_nodes: int, log_filename: str) -> str:
    output_dir = Path(log_filename).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / f"generated_Rb_line_{num_nodes}.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    return str(config_path)


def configure_bsm_nodes(
    network_topo: YbRouterNetTopo,
    detector_efficiency: float,
    detector_dark_count: float,
    eta1_converter_efficiency: float,
    eta2_converter_efficiency: float,
    converter_noise: float,
    bsm_operating_wavelength: int,
    bin_width: int,
    bin_separation: int,
) -> None:
    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type("HetTimeBinBSM")[0]
        bsm.update_detectors_params("efficiency", detector_efficiency)
        bsm.update_detectors_params("dark_count", detector_dark_count)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = True
            amzi.efficiency = eta2_converter_efficiency
            amzi.bin_width = bin_width
            amzi.bin_separation = bin_separation
            amzi.conversion_time = bin_separation
            amzi.input_encoding = "polarization"
            amzi.output_encoding = "rb_time_bin"

        for qfc in bsm_node.get_components_by_type("QFC"):
            qfc.input_wvln = 780
            qfc.output_wvln = bsm_operating_wavelength
            qfc.efficiency = eta1_converter_efficiency
            qfc.noise = converter_noise


def configure_router_nodes(
    network_topo: YbRouterNetTopo,
    name_to_app: dict,
    photon_collection_efficiency: float,
    eta1_converter_efficiency: float,
    eta2_converter_efficiency: float,
    converter_noise: float,
    imaging_loss_prob: float,
    image_interval: int,
    bsm_operating_wavelength: int,
    loading_time: int,
    cooling_time: int,
    bin_width: int,
    bin_separation: int,
) -> None:
    tl = network_topo.get_timeline()

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = HetRequestApp(node)

        for amzi in node.get_components_by_type("AmziConverter"):
            amzi.enabled = True
            amzi.efficiency = eta2_converter_efficiency
            amzi.bin_width = bin_width
            amzi.bin_separation = bin_separation
            amzi.conversion_time = bin_separation
            amzi.input_encoding = "polarization"
            amzi.output_encoding = "rb_time_bin"

        for qfc in node.get_components_by_type("QFC"):
            qfc.input_wvln = 780
            qfc.output_wvln = bsm_operating_wavelength
            qfc.efficiency = eta1_converter_efficiency
            qfc.noise = converter_noise

        for mem in node.get_components_by_type(MemoryArray)[0].memories:
            mem.efficiency = photon_collection_efficiency
            mem.original_memory_efficiency = photon_collection_efficiency
            mem.converter_output_wavelength = bsm_operating_wavelength
            mem.eta1converter_efficiency = eta1_converter_efficiency
            mem.eta2converter_efficiency = eta2_converter_efficiency
            mem.converter_noise = converter_noise
            mem.imaging_loss_prob = imaging_loss_prob
            mem.image_interval = image_interval
            mem.loading_time = loading_time
            mem.cooling_time = cooling_time
            mem.cool_time = cooling_time
            mem.converter_bin_width = bin_width
            mem.converter_bin_separation = bin_separation
            mem.bin_width = bin_width
            mem.bin_separation = bin_separation
            mem.update_next_attempt_timing()

        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = tl.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type("HetTimeBinBSM")[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)


def sum_attempts(nodes: list) -> int:
    return sum(
        mem.attempts
        for node in nodes
        for mem in node.get_components_by_type(MemoryArray)[0].memories
    )


def run_rb_line(args: argparse.Namespace) -> None:
    config = build_rb_line_config(
        args.num_nodes,
        args.memo_size,
        args.distance,
        args.attenuation,
        args.seed_offset,
        args.classical_delay,
    )
    network_config = write_generated_config(config, args.num_nodes, args.logfile)
    network_topo = YbRouterNetTopo(network_config)
    tl = network_topo.get_timeline()

    configure_bsm_nodes(
        network_topo,
        args.detectorefficiency,
        args.detectordarkcount,
        args.eta1converterefficiency,
        args.eta2converterefficiency,
        args.converternoise,
        args.bsm_operating_wavelength,
        args.binwidth,
        args.binseparation,
    )

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("WARNING")
    log.track_module("main_Rbnet_sim")
    log.track_module("generation")
    log.track_module("swapping")
    log.track_module("bsm")
    log.track_module("detector")
    log.track_module("memory")
    log.track_module("photon")
    log.track_module("apps")
    log.track_module("custom_node")
    log.track_module("time_bin_bsm")
    log.track_module("optical_channel")
    log.track_module("amziConverter")

    name_to_app = {}
    configure_router_nodes(
        network_topo,
        name_to_app,
        args.photoncollectionefficiency,
        args.eta1converterefficiency,
        args.eta2converterefficiency,
        args.converternoise,
        args.imaginglossprob,
        args.imageinterval,
        args.bsm_operating_wavelength,
        args.loadingtime,
        args.coolingtime,
        args.binwidth,
        args.binseparation,
    )

    routers = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)
    node_init = routers[0]
    node_resp = routers[-1]

    tl.init()

    total_time = 0
    delta = args.request_delay_ms * MILLISECOND
    reservation_duration = args.reservation_duration_s * SECOND

    for i in range(args.numtrials):
        basis = "Z" if i % 2 == 1 else "X"
        beginning = tl.now()
        starting_attempts = sum_attempts(routers)

        for node in routers:
            node.app.last_trap_time = beginning - node.app.time_in_trap

        name_to_app[node_init.name].start(
            node_resp.name,
            beginning + delta,
            beginning + reservation_duration,
            1,
            args.reservation_fidelity,
            basis,
        )
        name_to_app[node_init.name].basis = basis
        name_to_app[node_resp.name].basis = basis

        log.logger.warning(
            f"Starting Rb line {args.num_nodes}-node EG attempt at {tl.time}."
        )
        tl.run()

        entanglement_time = node_init.app.entanglement_time or node_resp.app.entanglement_time
        if entanglement_time is None:
            raise RuntimeError("No end-to-end entanglement was recorded before the timeline stopped.")

        taken_time = entanglement_time - beginning
        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("neg actual time")

        finishing_attempts = sum_attempts(routers)
        traversed_attempts = finishing_attempts - starting_attempts
        link_label = "swapped " if args.num_nodes > 2 else ""
        log.logger.warning(
            f"End-to-end entanglement num {i + 1} completed in {actual_time} seconds."
        )
        log.logger.warning(
            f"End-to-end entanglement num {i + 1} used {traversed_attempts} "
            f"{link_label}elementary-link attempts."
        )
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity_product = readout_fidelity0 * readout_fidelity1
    fid = node_init.app.get_fidelity(readout_fidelity_product)

    total_attempts = sum_attempts(routers)
    avg_time_label = "Average swapped ent time" if args.num_nodes > 2 else "Average ent time"
    pair_label = "end-to-end entanglement pairs" if args.num_nodes > 2 else "entanglement pairs"

    log.logger.warning(f"num_nodes:{args.num_nodes}")
    log.logger.warning(f"generated_config:{network_config}")
    log.logger.warning(f"pce:{args.photoncollectionefficiency}")
    log.logger.warning(f"loading_time:{args.loadingtime}")
    log.logger.warning(f"loading_time_ms:{args.loadingtime * 1e-9}")
    log.logger.warning(f"cooling_time:{args.coolingtime}")
    log.logger.warning(f"cooling_time_ms:{args.coolingtime * 1e-9}")
    log.logger.warning(
        f"After {args.numtrials} successful {pair_label}, calculated fidelity ={fid}"
    )
    log.logger.warning(f"{avg_time_label} is ~{total_time / args.numtrials}")
    log.logger.warning(
        f"{args.numtrials} {pair_label} were generated after {total_attempts} "
        f"elementary-link attempts; generation success rate: {args.numtrials / total_attempts}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an Rb-only line network with an arbitrary number of Rb nodes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    line = subparsers.add_parser("line", help="Run an Rb-only linear network.")
    line.add_argument("num_nodes", type=int, help="Number of Rb router nodes in the line.")
    line.add_argument("-pce", "--photoncollectionefficiency", type=float, default=0.5)
    line.add_argument("-n", "--numtrials", type=int, default=1000)
    line.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0)
    line.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.8)
    line.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=1389)
    line.add_argument("-eta1", "--eta1converterefficiency", type=float, default=0.99)
    line.add_argument("-eta2", "--eta2converterefficiency", type=float, default=0.98)
    line.add_argument("-converter_noise", "--converternoise", type=float, default=0.005)
    line.add_argument("-image_loss", "--imaginglossprob", type=float, default=0.095)
    line.add_argument("-image_interval", "--imageinterval", type=int, default=20)
    line.add_argument("-cool", "--coolingtime", type=int, default=1_000_000_000)
    line.add_argument("-load", "--loadingtime", type=int, default=10_000_000)
    line.add_argument("-bwidth", "--binwidth", type=int, default=520_000)
    line.add_argument("-bsep", "--binseparation", type=int, default=2_800_000)
    line.add_argument("-log", "--logfile", type=str, default="tmp/rb_line.log")
    line.add_argument("-memo_size", "--memo-size", dest="memo_size", type=int, default=10)
    line.add_argument("-distance", "--distance", type=float, default=500.0)
    line.add_argument("-attenuation", "--attenuation", type=float, default=0.0002)
    line.add_argument("-seed", "--seed-offset", dest="seed_offset", type=int, default=0)
    line.add_argument("-cc_delay", "--classical-delay", dest="classical_delay", type=int, default=1_000_000_000)
    line.add_argument("-request_delay", "--request-delay-ms", dest="request_delay_ms", type=int, default=20)
    line.add_argument(
        "-reservation_duration",
        "--reservation-duration-s",
        dest="reservation_duration_s",
        type=int,
        default=20,
    )
    line.add_argument("-reservation_fidelity", "--reservation-fidelity", type=float, default=0.1)
    line.set_defaults(func=run_rb_line)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
