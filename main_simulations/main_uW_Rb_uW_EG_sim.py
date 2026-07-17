"""
Transmon-Rb-transmon end-to-end entanglement-generation simulation.

Network:
    router_0 (uW) -- router_1 (Rb) -- router_2 (uW)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import StopOnSuccessHetRequestApp
from memory import MemoryArray
from yb_router_net_topo import YbRouterNetTopo


def configure_bsm_nodes(network_topo, args):
    bsm_hardware_name = "HetTimeBinBSM"

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params("efficiency", args.detectorefficiency)
        bsm.update_detectors_params("dark_count", args.detectordarkcount)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = True
            amzi.efficiency = args.eta2converterefficiency
            amzi.bin_width = args.binwidth
            amzi.bin_separation = args.binseparation
            amzi.conversion_time = args.binseparation
            amzi.input_encoding = "polarization"
            amzi.output_encoding = "rb_time_bin"

        bsm_qfc_wavelengths = {
            "BSM_0_1": {
                "QFC0": (args.uw_output_wavelength, args.bsm_operating_wavelength),
                "QFC1": (args.rb_telecom_wavelength, args.bsm_operating_wavelength),
            },
            "BSM_1_2": {
                "QFC1": (args.rb_telecom_wavelength, args.bsm_operating_wavelength),
                "QFC2": (args.uw_output_wavelength, args.bsm_operating_wavelength),
            },
        }

        if bsm_node.name not in bsm_qfc_wavelengths:
            raise ValueError(f"Unexpected BSM node {bsm_node.name}.")

        for qfc in bsm_node.get_components_by_type("QFC"):
            qfc_key = qfc.name.rsplit(".", 1)[-1]
            if qfc_key not in bsm_qfc_wavelengths[bsm_node.name]:
                raise ValueError(f"Unexpected QFC {qfc.name} on {bsm_node.name}.")

            qfc.input_wvln, qfc.output_wvln = bsm_qfc_wavelengths[bsm_node.name][qfc_key]
            qfc.efficiency = args.qfc_efficiency
            qfc.noise = args.qfc_noise


def configure_router_nodes(network_topo, args):
    tl = network_topo.get_timeline()
    bsm_hardware_name = "HetTimeBinBSM"
    name_to_app = {}

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = StopOnSuccessHetRequestApp(node)

        if node.memo_type == "uW":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.transducer_efficiency = args.transducer_efficiency
                mem.transducer_noise = args.transducer_noise
                mem.output_wavelength = args.uw_output_wavelength
                mem.coherence_time = args.transmon_coherence_time

        elif node.memo_type == "Rb":
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

            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = args.photoncollectionefficiency
                mem.original_memory_efficiency = args.photoncollectionefficiency
                mem.converter_output_wavelength = args.rb_telecom_wavelength
                mem.eta1converter_efficiency = args.eta1converterefficiency
                mem.eta2converter_efficiency = args.eta2converterefficiency
                mem.converter_noise = args.converternoise
                mem.imaging_loss_prob = args.imaginglossprob
                mem.image_interval = args.imageinterval
                mem.loading_time = args.loadingtime
                mem.cooling_time = args.coolingtime
                mem.cool_time = args.coolingtime
                mem.converter_bin_width = args.binwidth
                mem.converter_bin_separation = args.binseparation
                mem.bin_width = args.binwidth
                mem.bin_separation = args.binseparation
                mem.update_next_attempt_timing()

        else:
            raise ValueError(f"Only functional for Rb and uW memories, got {node.memo_type}.")

        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = tl.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)

    return name_to_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--numtrials", type=int, default=1000,
                        help="number of end-to-end entangled pairs to generate")
    parser.add_argument("-pce", "--photoncollectionefficiency", type=float, default=0.5,
                        help="Rb photon collection efficiency into fiber")
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0,
                        help="dark count rate in Hz for BSM detectors")
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85,
                        help="BSM detector efficiency")
    parser.add_argument("-rb_telecom_wvln", "--rb_telecom_wavelength", type=int, default=1389,
                        help="Rb fiber wavelength after router-side AMZI/QFC conversion")
    parser.add_argument("-uw_output_wvln", "--uw_output_wavelength", type=int, default=1550,
                        help="uW transducer optical output wavelength before BSM-side QFC")
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=746,
                        help="photon wavelength used at the transmon-Rb BSMs")
    parser.add_argument("-qfc_eff", "--qfc_efficiency", type=float, default=1.0,
                        help="BSM-side QFC efficiency")
    parser.add_argument("-qfc_noise", "--qfc_noise", type=float, default=0.005,
                        help="BSM-side QFC noise probability")
    parser.add_argument("-uw_noise", "--transducer_noise", type=float, default=0.047,
                        help="transmon transducer noise")
    parser.add_argument("-uw_efficiency", "--transducer_efficiency", type=float, default=0.6,
                        help="transmon transducer efficiency")
    parser.add_argument("-uw_coherence", "--transmon_coherence_time", type=int, default=500_000_000,
                        help="transmon T1 coherence time in ps")
    parser.add_argument("-eta1", "--eta1converterefficiency", type=float, default=0.99,
                        help="Rb router-side frequency conversion efficiency")
    parser.add_argument("-eta2", "--eta2converterefficiency", type=float, default=0.98,
                        help="Rb AMZI format conversion efficiency")
    parser.add_argument("-converter_noise", "--converternoise", type=float, default=0.005,
                        help="Rb router-side frequency conversion noise probability")
    parser.add_argument("-image_loss", "--imaginglossprob", type=float, default=0.095,
                        help="probability imaging finds the Rb atom lost")
    parser.add_argument("-image_interval", "--imageinterval", type=int, default=20,
                        help="number of Rb excitation cycles between imaging checks")
    parser.add_argument("-cool", "--coolingtime", type=int, default=1_000_000_000,
                        help="Rb cooling time in ps")
    parser.add_argument("-load", "--loadingtime", type=int, default=10_000_000,
                        help="Rb loading time in ps")
    parser.add_argument("-bwidth", "--binwidth", type=int, default=520_000,
                        help="converted time-bin width")
    parser.add_argument("-bsep", "--binseparation", type=int, default=2_800_000,
                        help="converted early-late bin separation")
    parser.add_argument("-log", "--logfile", type=str, default="tmp/uW_Rb_uW.log",
                        help="log file path")

    args = parser.parse_args()

    network_topo = YbRouterNetTopo("config/line_3_uW_Rb_uW.json")
    tl = network_topo.get_timeline()

    configure_bsm_nodes(network_topo, args)

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("WARNING")
    log.track_module("main_uW_Rb_uW_EG_sim")
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

    name_to_app = configure_router_nodes(network_topo, args)

    delta = 20 * MILLISECOND
    total_time = 0

    tl.init()

    routers = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)
    node_init = routers[0]
    node_mid = routers[1]
    node_resp = routers[2]

    for i in range(args.numtrials):
        basis = "Z" if i % 2 == 1 else "X"
        beginning = tl.now()
        starting_attempts_left = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        starting_attempts_mid = sum(mem.attempts for mem in node_mid.get_components_by_type(MemoryArray)[0].memories)
        starting_attempts_right = node_resp.get_components_by_type(MemoryArray)[0].memories[0].attempts
        tl.stop_time = beginning + 10000 * SECOND

        for node in routers:
            node.app.last_trap_time = beginning - node.app.time_in_trap

        name_to_app[node_init.name].start(
            node_resp.name,
            beginning + delta,
            beginning + 10000 * SECOND,
            1,
            0.1,
            basis,
        )
        name_to_app[node_init.name].basis = basis
        name_to_app[node_resp.name].basis = basis
        log.logger.warning(f"Starting uW-Rb-uW swapped EG attempt {i + 1} at {tl.time}.")
        tl.run()

        entanglement_time = node_init.app.entanglement_time or node_resp.app.entanglement_time
        if entanglement_time is None:
            raise RuntimeError("No end-to-end swapped entanglement was recorded before the timeline stopped.")

        taken_time = entanglement_time - beginning
        finishing_attempts_left = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        finishing_attempts_mid = sum(mem.attempts for mem in node_mid.get_components_by_type(MemoryArray)[0].memories)
        finishing_attempts_right = node_resp.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = (
            finishing_attempts_left - starting_attempts_left
            + finishing_attempts_mid - starting_attempts_mid
            + finishing_attempts_right - starting_attempts_right
        )

        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("Negative entanglement generation time.")

        log.logger.warning(f"End-to-end entanglement num {i + 1} completed in {actual_time} seconds.")
        log.logger.warning(f"End-to-end entanglement num {i + 1} used {traversed_attempts} elementary-link attempts.")
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    fid = node_init.app.get_fidelity(readout_fidelity0 * readout_fidelity1)
    total_attempts = sum(
        mem.attempts
        for node in routers
        for mem in node.get_components_by_type(MemoryArray)[0].memories
    )

    log.logger.warning(f"pce:{args.photoncollectionefficiency}")
    log.logger.warning(f"transmon_coherence:{args.transmon_coherence_time}")
    log.logger.warning(f"transducer_efficiency:{args.transducer_efficiency}")
    log.logger.warning(f"transducer_noise:{args.transducer_noise}")
    log.logger.warning(f"loading_time:{args.loadingtime}")
    log.logger.warning(f"loading_time_ms:{args.loadingtime * 1e-9}")
    log.logger.warning(f"cooling_time:{args.coolingtime}")
    log.logger.warning(f"cooling_time_ms:{args.coolingtime * 1e-9}")
    log.logger.warning(f"After {args.numtrials} successful uW-Rb-uW swapped entanglement attempts, calculated fidelity ={fid}")
    log.logger.warning(f"Average uW-Rb-uW swapped ent time is ~{total_time / args.numtrials}")
    log.logger.warning(
        f"{args.numtrials} end-to-end entanglement pairs were generated after {total_attempts} "
        f"elementary-link attempts; generation success rate: {args.numtrials / total_attempts}"
    )

    print(f"After {args.numtrials} successful uW-Rb-uW swapped entanglement attempts, calculated fidelity={fid}")
    print(f"Average uW-Rb-uW swapped entanglement time: {total_time / args.numtrials} seconds")
    print(f"Log written to {args.logfile}")


if __name__ == "__main__":
    main()
