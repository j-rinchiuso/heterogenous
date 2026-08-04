#NOTE EXAMPLE
# python main_simulations/main_twonode.py -n1 yb -n2 rb -n 1000 -log tmp/twonode_yb_rb.log

import argparse
import json
import sys
from dataclasses import dataclass, replace
from math import e
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import HetRequestApp
from memory import MemoryArray
from yb_router_net_topo import YbRouterNetTopo


MEMORY_TYPES = ("yb", "rb", "er", "uw")
SUPPORTED_PAIRS = {
    ("er", "er"),
    ("er", "rb"),
    ("er", "uw"),
    ("er", "yb"),
    ("rb", "rb"),
    ("rb", "uw"),
    ("rb", "yb"),
    ("uw", "uw"),
    ("uw", "yb"),
    ("yb", "yb"),
}
@dataclass(frozen=True)
class MemorySpec:
    template: str
    memo_type: str
    emitted_wavelength: int
    fiber_wavelength: int
    default_pce: float
@dataclass(frozen=True)
class LinkArchitecture:
    bsm_wavelength: int
MEMORIES = {
    "yb": MemorySpec("Yb1389", "Yb", 1389, 1389, 0.5),
    "rb": MemorySpec("Rb", "Rb", 780, 1389, 0.5),
    "er": MemorySpec("Er", "Er", 1532, 1532, 0.0792),
    
    "uw": MemorySpec("uW", "uW", 1550, 1550, 0.5),
}
ARCHITECTURES = {
    ("er", "er"): LinkArchitecture(bsm_wavelength=1532),
    ("er", "rb"): LinkArchitecture(bsm_wavelength=1532),
    ("er", "uw"): LinkArchitecture(bsm_wavelength=746),
    ("er", "yb"): LinkArchitecture(bsm_wavelength=746),
    ("rb", "rb"): LinkArchitecture(bsm_wavelength=1389),
    ("rb", "uw"): LinkArchitecture(bsm_wavelength=1550),
    ("rb", "yb"): LinkArchitecture(bsm_wavelength=1389),
    ("uw", "uw"): LinkArchitecture(bsm_wavelength=1550),
    ("uw", "yb"): LinkArchitecture(bsm_wavelength=746),
    ("yb", "yb"): LinkArchitecture(bsm_wavelength=1389),
}

def canonical_pair(node1: str, node2: str) -> tuple[str, str]:
    return tuple(sorted((node1, node2)))

def fiber_wavelength_for(memory_type: str, other_type: str) -> int:
    if memory_type == "rb":
        if other_type == "uw":
            return 1550
        if other_type == "er":
            return 1532
        return 1389
    return MEMORIES[memory_type].fiber_wavelength

def attenuation_for_wavelength(wavelength: int) -> float:
    if wavelength in (1532, 1550):
        return 0.0002
    if wavelength == 1389:
        return 0.0003
    if wavelength == 746:
        return 0.0002
    raise ValueError(f"No default attenuation configured for {wavelength} nm.")

def distance_to_bsm(memory_type: str, args) -> float:
    return args.distance

def configure_qfc_if_used(qfc, input_wavelength: int, output_wavelength: int, efficiency: float, noise: float) -> None:
    qfc.input_wvln = input_wavelength
    qfc.output_wvln = output_wavelength
    if input_wavelength == output_wavelength:
        qfc.efficiency = 1.0
        qfc.noise = 0.0
    else:
        qfc.efficiency = efficiency
        qfc.noise = noise

def build_two_node_config(args, specs: list[MemorySpec], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    node_distances = [distance_to_bsm(args.node1, args), distance_to_bsm(args.node2, args)]
    node_attenuations = [
        args.attenuation if args.attenuation is not None else attenuation_for_wavelength(specs[0].fiber_wavelength),
        args.attenuation if args.attenuation is not None else attenuation_for_wavelength(specs[1].fiber_wavelength)]
    router_distance = sum(node_distances)
    templates = {"het_time_bin": {"encoding_type": "het_time_bin"}}
    for spec in specs:
        templates[spec.template] = {"memo_type": spec.memo_type, "wavelength": str(spec.emitted_wavelength)}

    config = {
        "nodes": [
            {
                "name": "router_0",
                "type": "QuantumRouter",
                "template": specs[0].template,
                "seed": args.seed,
                "memo_size": 1,
                "group": 0,
            },
            {
                "name": "router_1",
                "type": "QuantumRouter",
                "template": specs[1].template,
                "seed": args.seed + 1,
                "memo_size": 1,
                "group": 0,
            },
            {
                "name": "BSM_0_1",
                "type": "BSMNode",
                "template": "het_time_bin",
                "seed": args.seed,
            },
        ],
        "qchannels": [
            {
                "name": "qchannel_0",
                "source": "router_0",
                "destination": "BSM_0_1",
                "distance": node_distances[0],
                "attenuation": node_attenuations[0],
            },
            {
                "name": "qchannel_1",
                "source": "router_1",
                "destination": "BSM_0_1",
                "distance": node_distances[1],
                "attenuation": node_attenuations[1],
            },
        ],
        "cchannels": [
            {"source": "BSM_0_1", "destination": "router_0", "distance": node_distances[0]},
            {"source": "router_0", "destination": "BSM_0_1", "distance": node_distances[0]},
            {"source": "BSM_0_1", "destination": "router_1", "distance": node_distances[1]},
            {"source": "router_1", "destination": "BSM_0_1", "distance": node_distances[1]},
            {"source": "router_0", "destination": "router_1", "distance": router_distance},
            {"source": "router_1", "destination": "router_0", "distance": router_distance},
        ],
        "templates": templates,
        "is_parallel": False,
    }

    output_path.write_text(json.dumps(config, indent=4))
    return output_path


def configure_bsm(network_topo, args, specs: list[MemorySpec], architecture: LinkArchitecture) -> None:
    bsm_hardware_name = "HetTimeBinBSM"
    bsm_wavelength = args.bsm_operating_wavelength or architecture.bsm_wavelength

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params("efficiency", args.detectorefficiency)
        bsm.update_detectors_params("dark_count", args.detectordarkcount)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = False

        for qfc in bsm_node.get_components_by_type("QFC"):
            if qfc.name.endswith("QFC0"):
                input_wavelength = specs[0].fiber_wavelength
            elif qfc.name.endswith("QFC1"):
                input_wavelength = specs[1].fiber_wavelength
            else:
                raise ValueError(f"Unexpected BSM-side QFC name {qfc.name}.")
            configure_qfc_if_used(qfc, input_wavelength, bsm_wavelength, args.qfc_efficiency, args.qfc_noise)


def configure_rb_node(node, args, pce: float, output_wavelength: int) -> None:
    for amzi in node.get_components_by_type("AmziConverter"):
        amzi.enabled = True
        amzi.efficiency = args.rb_eta2
        amzi.bin_width = args.rb_binwidth
        amzi.bin_separation = args.rb_binseparation
        amzi.conversion_time = args.rb_binseparation
        amzi.input_encoding = "polarization"
        amzi.output_encoding = "rb_time_bin"

    for qfc in node.get_components_by_type("QFC"):
        configure_qfc_if_used(qfc, 780, output_wavelength, args.rb_eta1, args.rb_converter_noise)

    for mem in node.get_components_by_type(MemoryArray)[0].memories:
        mem.efficiency = pce
        mem.original_memory_efficiency = pce
        mem.converter_output_wavelength = output_wavelength
        mem.eta1converter_efficiency = args.rb_eta1
        mem.eta2converter_efficiency = args.rb_eta2
        mem.converter_noise = args.rb_converter_noise
        mem.imaging_loss_prob = args.rb_imaging_loss_prob
        mem.image_interval = args.rb_image_interval
        mem.loading_time = args.rb_loading_time
        mem.cooling_time = args.rb_cooling_time
        mem.cool_time = args.rb_cooling_time
        mem.converter_bin_width = args.rb_binwidth
        mem.converter_bin_separation = args.rb_binseparation
        mem.bin_width = args.rb_binwidth
        mem.bin_separation = args.rb_binseparation
        mem.update_next_attempt_timing()


def configure_er_node(node, args, pce: float) -> None:
    for mem in node.get_components_by_type(MemoryArray)[0].memories:
        mem.efficiency = pce
        mem.original_memory_efficiency = pce
        mem.bin_width = args.er_binwidth
        mem.bin_separation = args.er_binseparation
        if args.er_coherence_time is not None:
            mem.coherence_time = args.er_coherence_time
            mem.spin_coherence_factor = e ** (-mem.spin_photon_generation_time / mem.coherence_time)
            mem.phase_flip_probability = (1 - mem.spin_coherence_factor)


def configure_yb_node(node, args, pce: float) -> None:
    for mem in node.get_components_by_type(MemoryArray)[0].memories:
        mem.efficiency = pce
        mem.original_memory_efficiency = pce
        mem.set_wavelength(1389)
        mem.retrap_num = args.yb_reload_count
        mem.bin_width = args.yb_binwidth


def configure_uw_node(node, args) -> None:
    for mem in node.get_components_by_type(MemoryArray)[0].memories:
        mem.transducer_efficiency = args.transducer_efficiency
        mem.transducer_noise = args.transducer_noise
        mem.output_wavelength = args.uw_output_wavelength
        mem.coherence_time = args.transmon_coherence_time


def configure_memory(node, args, pce: float, output_wavelength: int) -> None:
    if node.memo_type == "Rb":
        configure_rb_node(node, args, pce, output_wavelength)
    elif node.memo_type == "Er":
        configure_er_node(node, args, pce)
    elif node.memo_type == "Yb":
        configure_yb_node(node, args, pce)
    elif node.memo_type == "uW":
        configure_uw_node(node, args)
    else:
        raise ValueError(f"Unsupported memory type {node.memo_type}.")


def sync_bsm_time_bins(network_topo) -> None:
    bsm_hardware_name = "HetTimeBinBSM"
    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = network_topo.get_timeline().get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a two-node entanglement-generation simulation for selected memory types.")
    parser.add_argument("-n1", "--node1", choices=MEMORY_TYPES, required=True, help="left memory type")
    parser.add_argument("-n2", "--node2", choices=MEMORY_TYPES, required=True, help="right memory type")
    parser.add_argument("-n", "--numtrials", type=int, default=10000, help="successful pairs to generate")
    parser.add_argument("-log", "--logfile", type=str, default=None, help="log file path")
    parser.add_argument("-config_out", "--config_output", type=str, default=None, help="generated config path")
    parser.add_argument("-seed", "--seed", type=int, default=0, help="base random seed")
    parser.add_argument("-distance", "--distance", type=float, default=5000.0, help="distance from each node to BSM in m")
    parser.add_argument("-attenuation", "--attenuation", type=float, default=None, help="override channel attenuation for both node-to-BSM links")
    parser.add_argument("-pce", "--photoncollectionefficiency", type=float, default=None, help="common memory PCE")
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0, help="BSM dark count in Hz")
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85, help="BSM detector efficiency")
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=None, help="override BSM wavelength")
    parser.add_argument("-qfc_eff", "--qfc_efficiency", type=float, default=0.99, help="BSM-side QFC efficiency")
    parser.add_argument("-qfc_noise", "--qfc_noise", type=float, default=0.005, help="BSM-side QFC noise")

    parser.add_argument("-bwidth", "-rb_bwidth", "--binwidth", "--rb_binwidth", dest="rb_binwidth", type=int, default=520_000, help="Rb converted bin width in ps")
    parser.add_argument("-bsep", "-rb_bsep", "--binseparation", "--rb_binseparation", dest="rb_binseparation", type=int, default=2_800_000, help="Rb converted bin separation in ps")
    parser.add_argument("-rb_wvln", "--rb_telecom_wavelength", type=int, default=1389, help="Rb wavelength after router-side QFC")
    parser.add_argument("-eta1", "--rb_eta1", type=float, default=0.99, help="Rb router-side QFC efficiency")
    parser.add_argument("-eta2", "--rb_eta2", type=float, default=0.98, help="Rb router-side AMZI efficiency")
    parser.add_argument("-converter_noise", "--rb_converter_noise", type=float, default=0.005, help="Rb router-side QFC noise")
    parser.add_argument("-image_loss", "--rb_imaging_loss_prob", type=float, default=0.095, help="Rb imaging loss probability")
    parser.add_argument("-image_interval", "--rb_image_interval", type=int, default=20, help="Rb imaging interval")
    parser.add_argument("-cool", "--rb_cooling_time", type=int, default=1_000_000_000, help="Rb cooling time in ps")
    parser.add_argument("-load", "--rb_loading_time", type=int, default=10_000_000, help="Rb loading time in ps")

    parser.add_argument("-yb_reload", "--yb_reload_count", type=int, default=128, help="Yb attempts before reload")
    parser.add_argument("-yb_bwidth", "--yb_binwidth", type=int, default=520_000, help="Yb bin width in ps")

    parser.add_argument("-er_bwidth", "--er_binwidth", type=int, default=1_900_000, help="Er bin width in ps")
    parser.add_argument("-er_bsep", "--er_binseparation", type=int, default=22_200_000, help="Er bin separation in ps")
    parser.add_argument("-er_coh", "--er_coherence_time", type=int, default=23_000_000_000, help="Er coherence time in ps")

    parser.add_argument("-uw_output_wvln", "--uw_output_wavelength", type=int, default=1550, help="uW transducer optical output wavelength")
    parser.add_argument("-uw_noise", "--transducer_noise", type=float, default=0.047, help="uW transducer noise")
    parser.add_argument("-uw_efficiency", "--transducer_efficiency", type=float, default=0.6, help="uW transducer efficiency")
    parser.add_argument("-uw_coherence", "--transmon_coherence_time", type=int, default=500_000_000, help="transmon T1 coherence time in ps")
    return parser.parse_args()


def main():
    args = parse_args()
    pair = canonical_pair(args.node1, args.node2)
    if pair not in SUPPORTED_PAIRS:
        raise NotImplementedError(f"{args.node1}-{args.node2} is not wired yet. Add its wavelength/converter rules to ARCHITECTURES.")

    specs = [replace(MEMORIES[args.node1], fiber_wavelength=fiber_wavelength_for(args.node1, args.node2)),
             replace(MEMORIES[args.node2], fiber_wavelength=fiber_wavelength_for(args.node2, args.node1))]
    architecture = ARCHITECTURES[pair]
    default_log = f"tmp/twonode_{args.node1}_{args.node2}.log"
    args.logfile = args.logfile or default_log
    config_output = Path(args.config_output or f"tmp/two_node_topologies/generated_twonode_{args.node1}_{args.node2}.json")
    config_path = build_two_node_config(args, specs, config_output)

    network_topo = YbRouterNetTopo(str(config_path))
    tl = network_topo.get_timeline()
    configure_bsm(network_topo, args, specs, architecture)

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("DEBUG")
    for module in (
        "main_twonode",
        #"timeline"
       # "generation",
        #"bsm",
        #"detector",
        #"memory",
        #"photon",
        #"apps",
        #"custom_node",
        #"time_bin_bsm",
        #"optical_channel",
        #amziConverter",
        #"qfc",
    ):
        log.track_module(module)

    name_to_app = {}
    routers = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)
    for index, node in enumerate(routers):
        name_to_app[node.name] = HetRequestApp(node)
        pce = args.photoncollectionefficiency
        if pce is None:
            pce = specs[index].default_pce
        configure_memory(node, args, pce, specs[index].fiber_wavelength)

    sync_bsm_time_bins(network_topo)

    delta = 20 * MILLISECOND
    total_time = 0
    tl.init()
    node_init, node_resp = routers

    for i in range(args.numtrials):
        basis = ["X", "Y", "Z"][i % 3]
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts

        for node in routers:
            node.app.last_trap_time = beginning - node.app.time_in_trap

        app: HetRequestApp = name_to_app[node_init.name]
        start_time = beginning + delta
        end_time = beginning + 100 * SECOND
        #print(f'{i}:beginning: {beginning}, start_time: {start_time}, end_time: {end_time}')
        app.start(node_resp.name, start_time, end_time, 1, 0.1, basis)

        app.basis = basis
        #log.logger.warning(f"Starting {args.node1}-{args.node2} EG attempt {i + 1} at {tl.time}.")
        tl.run()

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("Negative entanglement time.")

        #log.logger.warning(f"Entanglement num {i + 1} completed in {actual_time} seconds.")
        #log.logger.warning(f"Entanglement num {i + 1} took {traversed_attempts} attempts.")
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    fid = node_init.app.get_fidelity(readout_fidelity0 * readout_fidelity1)
    fid_best_estimate = node_init.app.get_fidelity_best_estimate(readout_fidelity0 * readout_fidelity1)
    fid_precise = node_init.app.get_precise_fidelity(readout_fidelity0 * readout_fidelity1)
    attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
    average_time = total_time / args.numtrials

    log.logger.warning(f"node1:{args.node1}")
    log.logger.warning(f"node2:{args.node2}")
    log.logger.warning(f"node1_fiber_wavelength:{specs[0].fiber_wavelength}")
    log.logger.warning(f"node2_fiber_wavelength:{specs[1].fiber_wavelength}")
    log.logger.warning(f"node1_bsm_distance:{distance_to_bsm(args.node1, args)}")
    log.logger.warning(f"node2_bsm_distance:{distance_to_bsm(args.node2, args)}")
    log.logger.warning(f"node1_attenuation:{args.attenuation if args.attenuation is not None else attenuation_for_wavelength(specs[0].fiber_wavelength)}")
    log.logger.warning(f"node2_attenuation:{args.attenuation if args.attenuation is not None else attenuation_for_wavelength(specs[1].fiber_wavelength)}")
    log.logger.warning(f"bsm_operating_wavelength:{args.bsm_operating_wavelength or architecture.bsm_wavelength}")
    log.logger.warning(f"config:{config_path}")
    log.logger.warning(f"default_node_bsm_distance:{args.distance}")
    log.logger.warning(f"After {args.numtrials} successful entanglement attempts, calculated fidelity ={fid}")
    log.logger.warning(f"After {args.numtrials} successful entanglement attempts, calculated best estimate fidelity ={fid_best_estimate}")
    log.logger.warning(f"After {args.numtrials} successful entanglement attempts, calculated precise fidelity ={fid_precise}")
    log.logger.warning(f"Average ent time is ~{average_time}")
    log.logger.warning(
        f"{args.numtrials} entanglement pairs were generated after {attempts} attempts; "
        f"generation success rate: {args.numtrials / attempts}")

    print(f"After {args.numtrials} successful {args.node1}-{args.node2} entanglement attempts, fidelity={fid}")
    print(f"After {args.numtrials} successful {args.node1}-{args.node2} entanglement attempts, best estimate fidelity={fid_best_estimate}")
    print(f"After {args.numtrials} successful {args.node1}-{args.node2} entanglement attempts, precise fidelity={fid_precise}")
    print(f"Average entanglement time: {average_time} seconds")
    print(f"Log written to {args.logfile}")


if __name__ == "__main__":
    main()
