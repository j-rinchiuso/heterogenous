"""
router_0 (uW) -- router_1 (Yb) -- router_2 (Er)
"""

import argparse
import sys
from math import e
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sequence.constants import MILLISECOND, SECOND
from sequence.utils import log

from apps import HetRequestApp
from memory import MemoryArray
from yb_router_net_topo import YbRouterNetTopo


def configure_bsm_nodes(network_topo, detector_efficiency, detector_dark_count, bsm_wavelength, 
                        yb_wavelength, er_wavelength, uw_output_wavelength, qfc_efficiency, qfc_noise):
    bsm_hardware_name = "HetTimeBinBSM"

    bsm_qfc_wavelengths = {
        "BSM_0_1": {
            "QFC0": (uw_output_wavelength, bsm_wavelength),
            "QFC1": (yb_wavelength, bsm_wavelength),
        },
        "BSM_1_2": {
            "QFC1": (yb_wavelength, bsm_wavelength),
            "QFC2": (er_wavelength, bsm_wavelength),
        },
    }

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params("efficiency", detector_efficiency)
        bsm.update_detectors_params("dark_count", detector_dark_count)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = False

        if bsm_node.name not in bsm_qfc_wavelengths:
            raise ValueError(f"Unexpected BSM node {bsm_node.name}.")

        for qfc in bsm_node.get_components_by_type("QFC"):
            qfc_key = qfc.name.rsplit(".", 1)[-1]
            if qfc_key not in bsm_qfc_wavelengths[bsm_node.name]:
                raise ValueError(f"Unexpected QFC {qfc.name} on {bsm_node.name}.")
            input_wavelength, output_wavelength = bsm_qfc_wavelengths[bsm_node.name][qfc_key]
            qfc.input_wvln = input_wavelength
            qfc.output_wvln = output_wavelength
            qfc.efficiency = qfc_efficiency
            qfc.noise = qfc_noise


def configure_router_nodes(network_topo, yb_photon_collection_efficiency, er_photon_collection_efficiency, 
                           yb_wavelength, er_bin_width, er_bin_separation, er_coherence_time, 
                           transducer_efficiency, transducer_noise, transmon_coherence_time, uw_output_wavelength):
    tl = network_topo.get_timeline()
    bsm_hardware_name = "HetTimeBinBSM"
    name_to_app = {}

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = HetRequestApp(node)
        

        if node.memo_type == "uW":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.transducer_efficiency = transducer_efficiency
                mem.transducer_noise = transducer_noise
                mem.output_wavelength = uw_output_wavelength
                mem.coherence_time = transmon_coherence_time

        elif node.memo_type == "Yb":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = yb_photon_collection_efficiency
                mem.original_memory_efficiency = yb_photon_collection_efficiency
                mem.set_wavelength(yb_wavelength)

        elif node.memo_type == "Er":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = er_photon_collection_efficiency
                mem.original_memory_efficiency = er_photon_collection_efficiency
                mem.bin_width = er_bin_width
                mem.bin_separation = er_bin_separation
                mem.coherence_time = er_coherence_time
                mem.spin_coherence_factor = e ** (-mem.spin_photon_generation_time / mem.coherence_time)
                mem.phase_flip_probability = 1 - mem.spin_coherence_factor

        else:
            raise ValueError(f"Memory type {node.memo_type} not supported.")

        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = tl.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)

    return name_to_app
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--numtrials", type=int, default=1002, help="number of end-to-end entanglement pairs to generate")
    parser.add_argument("-config", "--configfile", type=str, default="config/line_3_uW_Yb_Er.json", help="network config file")
    parser.add_argument("-log", "--logfile", type=str, default="tmp/uW_yb_er.log", help="log file path")
    parser.add_argument("-yb_pce", "--ybphotoncollectionefficiency", type=float, default=0.5, help="Yb photon collection efficiency")
    parser.add_argument("-er_pce", "--erphotoncollectionefficiency", type=float, default=0.0792, help="Er photon collection/source efficiency")
    parser.add_argument("-ybwavelength", "--ybphotonwavelength", type=int, default=1389, help="Yb emitted photon wavelength")
    parser.add_argument("-er_wvln", "--erphotonwavelength", type=int, default=1532, help="Er emitted photon wavelength")
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=746, help="photon wavelength used at both BSMs")
    parser.add_argument("-qfc_eff", "--qfc_efficiency", type=float, default=0.99, help="BSM-side QFC efficiency")
    parser.add_argument("-qfc_noise", "--qfc_noise", type=float, default=0.005, help="BSM-side QFC noise probability")
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0, help="detector dark count rate in Hz")
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85, help="BSM detector efficiency")
    parser.add_argument("-uw_output_wvln", "--uw_output_wavelength", type=int, default=1550, 
                        help="uW transducer optical output wavelength before BSM-side QFC")
    parser.add_argument("-uw_noise", "--transducer_noise", type=float, default=0.047, help="transmon transducer noise")
    parser.add_argument("-uw_efficiency", "--transducer_efficiency", type=float, default=0.6, help="transmon transducer efficiency")
    parser.add_argument("-uw_coherence", "--transmon_coherence_time", type=int, default=500_000_000, help="transmon coherence time in ps")
    parser.add_argument("-er_bwidth", "--er_binwidth", type=int, default=1_900_000, help="Er time-bin width in ps")
    parser.add_argument("-er_bsep", "--er_binseparation", type=int, default=22_200_000, help="Er early-late bin separation in ps")
    parser.add_argument("-er_coh", "--er_coherence_time", type=int, default=23_000_000_000, help="Er spin coherence time in ps")

    args = parser.parse_args()

    network_topo = YbRouterNetTopo(args.configfile)
    configure_bsm_nodes(network_topo, args.detectorefficiency, args.detectordarkcount, 
                        args.bsm_operating_wavelength, args.ybphotonwavelength, args.erphotonwavelength, 
                        args.uw_output_wavelength, args.qfc_efficiency, args.qfc_noise)
    
    tl = network_topo.get_timeline()

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("WARNING")
    modules = ["main_uW_yb_er MAIN"]
    for module in modules:
        log.track_module(module)
    
    name_to_app = configure_router_nodes(network_topo, args.ybphotoncollectionefficiency, 
                                        args.erphotoncollectionefficiency, args.ybphotonwavelength, 
                                        args.er_binwidth, args.er_binseparation, args.er_coherence_time, 
                                        args.transducer_efficiency, args.transducer_noise, 
                                        args.transmon_coherence_time, args.uw_output_wavelength)

    delta = 20 * MILLISECOND 
    total_time = 0

    tl.init()
    
    routers = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)
    node_init = routers[0]
    node_resp = routers[2]

    for i in range(args.numtrials):
        basis = ["X", "Y", "Z"][i % 3]
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts

        for node in routers:
            node.app.entanglement_time = None
            node.app.entanglement_failed_time = None
            node.app.last_trap_time = beginning - node.app.time_in_trap

        app: HetRequestApp = name_to_app[node_init.name]
        start_time = beginning + delta
        end_time = beginning + 25 * SECOND
        app.start(node_resp.name, start_time, end_time, 1, 0.1, basis)

        app.basis = basis
        log.logger.warning(f"Starting uW-Yb-Er EG attempt {i + 1} at {tl.time}.")
        tl.run()

        if node_init.app.entanglement_time is None:
            raise RuntimeError(f"End-to-end entanglement attempt {i + 1} did not complete.")

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("Negative entanglement generation time.")


        #log.logger.warning(f"End-to-end entanglement num {i + 1} completed in {actual_time} seconds.")
       # log.logger.warning(f"End-to-end entanglement num {i + 1} used {traversed_attempts} initiator attempts.")
        total_time += actual_time


    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    x_trials = sum(node_init.app.meas_results[f"X_{i}{i}"] for i in range(1, 5))
    y_trials = sum(node_init.app.meas_results[f"Y_{i}{i}"] for i in range(1, 5))
    z_trials = sum(node_init.app.meas_results[f"Z_{i}{i}"] for i in range(1, 5))
    fid = None
    fid_best_estimate = None
    fid_precise = None
    if x_trials > 0 and z_trials > 0:
        fid = node_init.app.get_fidelity(readout_fidelity0 * readout_fidelity1)
        fid_best_estimate = node_init.app.get_fidelity_best_estimate(readout_fidelity0 * readout_fidelity1)
    if x_trials > 0 and y_trials > 0 and z_trials > 0:
        fid_precise = node_init.app.get_precise_fidelity(readout_fidelity0 * readout_fidelity1)
    attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts

    #log.logger.warning(f"config:{args.configfile}")
    #log.logger.warning(f"bsm_operating_wavelength:{args.bsm_operating_wavelength}")
    log.logger.warning(f"After {args.numtrials} successful end-to-end entanglement attempts, calculated fidelity={fid}")
    log.logger.warning(f"After {args.numtrials} successful end-to-end entanglement attempts, calculated best estimate fidelity={fid_best_estimate}")
    log.logger.warning(f"After {args.numtrials} successful end-to-end entanglement attempts, calculated precise fidelity={fid_precise}")
    log.logger.warning(f"Average three-node end-to-end entanglement time is ~{total_time / args.numtrials}")
    log.logger.warning(f"{args.numtrials} end-to-end entanglement pairs were generated after {attempts} initiator attempts.")
 


if __name__ == "__main__":
    main()
