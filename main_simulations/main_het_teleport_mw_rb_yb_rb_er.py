

from __future__ import annotations

import argparse
import sys
from math import sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import HetRequestApp
from het_teleport_app import HetTeleportApp
from memory import HetMemoryArray, MemoryArray
from yb_router_net_topo import YbRouterNetTopo


DEFAULT_CONFIG = "config/teleport_mw_rb_yb_rb_er.json"
DEFAULT_INPUT_STATE = [complex(sqrt(0.5)), complex(sqrt(0.5))] #random state


def parse_args():
    parser = argparse.ArgumentParser(description="Teleport Mw data to Er over an Rb-Yb-Rb communication network.")
    parser.add_argument("-config", "--configfile", type=str, default=DEFAULT_CONFIG, help="Rb-Yb-Rb network configuration file.")
    parser.add_argument("-n", "--numtrials", type=int, default=100, help="number of teleportation trials")
    parser.add_argument("-log", "--logfile", type=str, default="tmp/het_teleport_mw_rb_yb_rb_er.log", help="log file path")
    parser.add_argument("-pce", "--photoncollectionefficiency", type=float, default=0.5)
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0) 
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85)
    parser.add_argument("-ybwavelength", "--ybphotonwavelength", type=int, default=1389)
    parser.add_argument("-rb_telecom_wvln", "--rb_telecom_wavelength", type=int, default=1389)
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=1389)
    parser.add_argument("-eta1", "--eta1converterefficiency", type=float, default=0.99)
    parser.add_argument("-eta2", "--eta2converterefficiency", type=float, default=0.98)
    parser.add_argument("-converter_noise", "--converternoise", type=float, default=0.005)
    parser.add_argument("-image_loss", "--imaginglossprob", type=float, default=0.095)
    parser.add_argument("-image_interval", "--imageinterval", type=int, default=20)
    parser.add_argument("-bwidth", "--binwidth", type=int, default=520_000)
    parser.add_argument("-bsep", "--binseparation", type=int, default=2_800_000)
    return parser.parse_args()


def configure_bsm_nodes(network_topo, args) -> None:

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type("HetTimeBinBSM")[0]
        bsm.update_detectors_params("efficiency", args.detectorefficiency)
        bsm.update_detectors_params("dark_count", args.detectordarkcount)
        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = False
        for qfc in bsm_node.get_components_by_type("QFC"):
            qfc.input_wvln = args.rb_telecom_wavelength
            qfc.output_wvln = args.bsm_operating_wavelength
            qfc.efficiency = 1.0
            qfc.noise = 0.0


def configure_communication_nodes(network_topo, args) -> None:
    timeline = network_topo.get_timeline()
    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        if node.memo_type == "Rb":
            for amzi in node.get_components_by_type("AmziConverter"):
                amzi.enabled = True
                amzi.efficiency = args.eta2converterefficiency
                amzi.bin_width = args.binwidth
                amzi.bin_separation = args.binseparation
                amzi.conversion_time = args.binseparation
                amzi.input_encoding = "polarization"
                amzi.output_encoding = "rb_time_bin"
            for qfc in node.get_components_by_type("QFC"):
                qfc.input_wvln = 780
                qfc.output_wvln = args.rb_telecom_wavelength
                qfc.efficiency = args.eta1converterefficiency
                qfc.noise = args.converternoise
            for memory in node.get_components_by_type(MemoryArray)[0].memories:
                memory.efficiency = args.photoncollectionefficiency
                memory.original_memory_efficiency = args.photoncollectionefficiency
                memory.converter_output_wavelength = args.rb_telecom_wavelength
                memory.eta1converter_efficiency = args.eta1converterefficiency
                memory.eta2converter_efficiency = args.eta2converterefficiency
                memory.converter_noise = args.converternoise
                memory.imaging_loss_prob = args.imaginglossprob
                memory.image_interval = args.imageinterval
                memory.converter_bin_width = args.binwidth
                memory.converter_bin_separation = args.binseparation
                memory.bin_width = args.binwidth
                memory.bin_separation = args.binseparation
                memory.update_next_attempt_timing()
        elif node.memo_type == "Yb":
            for memory in node.get_components_by_type(MemoryArray)[0].memories:
                memory.efficiency = args.photoncollectionefficiency
                memory.original_memory_efficiency = args.photoncollectionefficiency
                memory.set_wavelength(args.ybphotonwavelength)
        else:
            raise ValueError(f"Expected only Rb and Yb communication memories, got {node.memo_type}.")
        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels:
            bsm_node = timeline.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type("HetTimeBinBSM")[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)
def create_data_memory_array(node, memory_type: str) -> HetMemoryArray:
    """Create one local data memory WITHOUT adding it to network reservations."""
    data_memory_array = HetMemoryArray(f"{node.name}.DataMemoryArray", node.timeline, memory_type=memory_type, num_memories=1, cutoff_flag=False,)
    node.add_component(data_memory_array)
    for memory in data_memory_array.memories:
        # Local data memories are not managed by the communication-memory
        # resource manager, so they shoul NOT tell resource network manager
        memory.cutoff_flag = False
        memory.is_in_application = True
    return data_memory_array


def main():
    args = parse_args()
    network_topo = YbRouterNetTopo(args.configfile)
    timeline = network_topo.get_timeline()
    configure_bsm_nodes(network_topo, args)
    configure_communication_nodes(network_topo, args)
    alice = timeline.get_entity_by_name("alice")
    bob = timeline.get_entity_by_name("bob")
    core_yb = timeline.get_entity_by_name("core_yb")
    if alice is None or bob is None or core_yb is None:
        raise ValueError("Config must define alice, core_yb, and bob routers")
    if alice.memo_type != "Rb" or core_yb.memo_type != "Yb" or bob.memo_type != "Rb":
        raise ValueError("Communication architecture must be Rb-Yb-Rb for this sim (check to make sure its that and working)")
    alice_data_array = create_data_memory_array(alice, "uW")
    bob_data_array = create_data_memory_array(bob, "Er")
    alice_app = HetTeleportApp(alice, alice_data_array)
    bob_app = HetTeleportApp(bob, bob_data_array)
    HetRequestApp(core_yb)
    log_path = Path(args.logfile)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log.set_logger(__name__, timeline, str(log_path))
    log.set_logger_level("WARNING")
    for module in ("main_het_teleport_mw_rb_yb_rb_er",):#"generation", "swapping", "het_teleport_app", "het_teleportation","action_condition_set"):
        log.track_module(module)

    timeline.init()
    successful_teleports = 0
    delta = 20 * MILLISECOND
    request_window = 20 * SECOND

    for trial in range(args.numtrials):
        alice_data_array[0].update_state(DEFAULT_INPUT_STATE)
        bob_data_array[0].update_state([complex(1), complex(0)])
        results_before = len(bob_app.results)
        beginning = timeline.now()
        for node in (alice, core_yb, bob):
            node.app.last_trap_time = beginning - node.app.time_in_trap
        alice_app.start(responder=bob.name, start_t=beginning + delta, end_t=beginning + request_window, memory_size=1, fidelity=0.1, data_memory_index=0, bob_data_memory_index=0,)
        log.logger.warning(f"Starting Mw-to-Er teleportation trial {trial + 1} at {beginning}.")
        timeline.run()

        succeeded = len(bob_app.results) > results_before
        successful_teleports += int(succeeded)
        if not succeeded:
            # Reservation expiry releases communication memories/rules. Remove
            # unmatched app-level protocol objects before the next trial.
            alice_app.teleport_protocols.clear()
            bob_app.teleport_protocols.clear()
        log.logger.warning(
            f"Mw-to-Er teleportation trial {trial + 1} "
            f"{'succeeded' if succeeded else 'failed'}.")

    success_percent = 100 * successful_teleports / args.numtrials
    summary = (
        f"Teleport success: {successful_teleports}/{args.numtrials} "
        f"({success_percent:.2f}%)")
    log.logger.warning(summary) 

if __name__ == "__main__":
    main()
