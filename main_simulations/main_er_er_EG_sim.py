import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import HetRequestApp
from memory import MemoryArray
from yb_router_net_topo import YbRouterNetTopo
ER_PHOTON_WAVELENGTH=1532


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-pce", "--photoncollectionefficiency", type=float, default=1.0, help="extra Er source efficiency multiplier; keep at 1.0 unless adding loss beyond cavity/grating")
    parser.add_argument("-n", "--numtrials", type=int, default=1000, help="number of entangled pairs to generate")
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=6.0, help="dark count rate in Hz for BSM detectors")
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85, help="BSM detector efficiency")
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=float, default=1532, help="photon wavelength used at the BSM")
    parser.add_argument("-qfc_eff", "--qfc_efficiency", type=float, default=1.0, help="efficiency of BSM-side QFCs; pass-through by default")
    parser.add_argument("-qfc_noise", "--qfc_noise", type=float, default=0.0, help="noise probability for BSM-side QFCs")
    parser.add_argument("-bwidth", "--binwidth", type=int, default=1_900_000, help="Er heralding time-bin width in ps")
    parser.add_argument("-bsep", "--binseparation", type=int, default=75_500_000, help="Er early-late bin separation in ps")
    parser.add_argument("-log", "--logfile", type=str, default="tmp/er_er.log", help="log file path")

    args = parser.parse_args()

    network_topo = YbRouterNetTopo("config/linearErEr.json")
    tl = network_topo.get_timeline()
    bsm_hardware_name = "HetTimeBinBSM"

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params("efficiency", args.detectorefficiency)
        bsm.update_detectors_params("dark_count", args.detectordarkcount)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = False

        for qfc in bsm_node.get_components_by_type("QFC"):
            qfc.input_wvln = ER_PHOTON_WAVELENGTH
            qfc.output_wvln = args.bsm_operating_wavelength
            qfc.efficiency = args.qfc_efficiency
            qfc.noise = args.qfc_noise

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("WARNING")
    log.track_module("main_er_er_EG_sim")
    log.track_module("generation")
    log.track_module("bsm")
    log.track_module("detector")
    log.track_module("memory")
    log.track_module("photon")
    log.track_module("apps")
    log.track_module("custom_node")
    log.track_module("time_bin_bsm")
    log.track_module("optical_channel")
    log.track_module("qfc")

    total_time = 0
    name_to_app = {}

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = HetRequestApp(node)

        if node.memo_type != "Er":
            raise ValueError(f"Only functional for Er memories, got {node.memo_type}.")

        for mem in node.get_components_by_type(MemoryArray)[0].memories:
            mem.efficiency = args.photoncollectionefficiency
            mem.original_memory_efficiency = args.photoncollectionefficiency
            mem.bin_width = args.binwidth
            mem.bin_separation = args.binseparation

        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = tl.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)

    delta = 20 * MILLISECOND
    tl.init()

    node_init = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[0]
    node_resp = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[1]

    for i in range(args.numtrials):
        basis = "Z" if i % 2 == 1 else "X"
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts

        for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
            node.app.last_trap_time = beginning - node.app.time_in_trap

        name_to_app[node_init.name].start(
            node_resp.name,
            beginning + delta,
            beginning + 10000 * SECOND,
            1,
            0.1,
            basis,
        )
        name_to_app[node_resp.name].basis = basis
        log.logger.warning(f"Starting Er-Er EG attempt {i + 1} at {tl.time}.")
        tl.run()

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("Negative entanglement time.")

        log.logger.warning(f"Entanglement num {i + 1} completed in {actual_time} seconds.")
        log.logger.warning(f"Entanglement num {i + 1} took {traversed_attempts} attempts.")
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    fid = node_init.app.get_fidelity(readout_fidelity0 * readout_fidelity1)
    attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts




    log.logger.warning(f"After {args.numtrials} successful entanglement attempts, calculated fidelity ={fid}")
    log.logger.warning(f"Average ent time is ~{total_time / args.numtrials}")
    log.logger.warning(
        f"{args.numtrials} entanglement pairs were generated after {attempts} attempts; "
        f"generation success rate: {args.numtrials / attempts}"
    )


if __name__ == "__main__":
    main()
