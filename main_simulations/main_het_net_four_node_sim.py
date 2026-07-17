"""
Four-node
router_0 (uW) -- router_1 (Yb) -- router_2 (Rb) -- router_3 (uW)
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


def configure_bsm_nodes(
        network_topo,
        detector_efficiency,
        detector_dark_count,
        hetero_bsm_wavelength,
        atom_bsm_wavelength,
        yb_wavelength,
        rb_telecom_wavelength,
        uw_output_wavelength,
        qfc_efficiency,
        qfc_noise,
        rb_eta2_efficiency,
        rb_bin_width,
        rb_bin_separation):
    bsm_hardware_name = "HetTimeBinBSM"

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params("efficiency", detector_efficiency)
        bsm.update_detectors_params("dark_count", detector_dark_count)

        for amzi in bsm_node.get_components_by_type("AmziConverter"):
            amzi.enabled = True
            amzi.efficiency = rb_eta2_efficiency
            amzi.bin_width = rb_bin_width
            amzi.bin_separation = rb_bin_separation
            amzi.conversion_time = rb_bin_separation
            amzi.input_encoding = "polarization"
            amzi.output_encoding = "rb_time_bin"

        # Four-node layout:
        # BSM_0_1 is uW-Yb, so both arms convert to 746 nm.
        # BSM_1_2 is Yb-Rb, so both arms stay/pass through at 1389 nm.
        # BSM_2_3 is Rb-uW, so both arms convert to 746 nm.
        bsm_qfc_wavelengths = {
            "BSM_0_1": {
                "QFC0": (uw_output_wavelength, hetero_bsm_wavelength),
                "QFC1": (yb_wavelength, hetero_bsm_wavelength),
            },
            "BSM_1_2": {
                "QFC1": (yb_wavelength, atom_bsm_wavelength),
                "QFC2": (rb_telecom_wavelength, atom_bsm_wavelength),
            },
            "BSM_2_3": {
                "QFC2": (rb_telecom_wavelength, hetero_bsm_wavelength),
                "QFC3": (uw_output_wavelength, hetero_bsm_wavelength),
            },
        }

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


def configure_router_nodes(
        network_topo,
        photon_collection_efficiency,
        yb_wavelength,
        transducer_efficiency,
        transducer_noise,
        transmon_coherence_time,
        rb_telecom_wavelength,
        uw_output_wavelength,
        rb_eta1_efficiency,
        rb_eta2_efficiency,
        rb_converter_noise,
        rb_imaging_loss_prob,
        rb_image_interval,
        rb_loading_time,
        rb_cooling_time,
        rb_bin_width,
        rb_bin_separation):
    tl = network_topo.get_timeline()
    bsm_hardware_name = "HetTimeBinBSM"
    name_to_app = {}

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = StopOnSuccessHetRequestApp(node)

        if node.memo_type == "Yb":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = photon_collection_efficiency
                mem.original_memory_efficiency = photon_collection_efficiency
                mem.set_wavelength(yb_wavelength)

        elif node.memo_type == "uW":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.transducer_efficiency = transducer_efficiency
                mem.transducer_noise = transducer_noise
                mem.output_wavelength = uw_output_wavelength
                mem.coherence_time = transmon_coherence_time

        elif node.memo_type == "Rb":
            for amzi in node.get_components_by_type("AmziConverter"):
                amzi.enabled = True
                amzi.efficiency = rb_eta2_efficiency
                amzi.bin_width = rb_bin_width
                amzi.bin_separation = rb_bin_separation
                amzi.conversion_time = rb_bin_separation
                amzi.input_encoding = "polarization"
                amzi.output_encoding = "rb_time_bin"

            for qfc in node.get_components_by_type("QFC"):
                qfc.input_wvln = 780
                qfc.output_wvln = rb_telecom_wavelength
                qfc.efficiency = rb_eta1_efficiency
                qfc.noise = rb_converter_noise

            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = photon_collection_efficiency
                mem.original_memory_efficiency = photon_collection_efficiency
                mem.converter_output_wavelength = rb_telecom_wavelength
                mem.eta1converter_efficiency = rb_eta1_efficiency
                mem.eta2converter_efficiency = rb_eta2_efficiency
                mem.converter_noise = rb_converter_noise
                mem.imaging_loss_prob = rb_imaging_loss_prob
                mem.image_interval = rb_image_interval
                mem.loading_time = rb_loading_time
                mem.cooling_time = rb_cooling_time
                mem.cool_time = rb_cooling_time
                mem.converter_bin_width = rb_bin_width
                mem.converter_bin_separation = rb_bin_separation
                mem.bin_width = rb_bin_width
                mem.bin_separation = rb_bin_separation
                mem.update_next_attempt_timing()

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
    parser.add_argument("-n", "--numtrials", type=int, default=1000,
                        help="number of end-to-end entanglement pairs to generate")
    parser.add_argument("-pce", "--photoncollectionefficiency", type=float, default=0.5,
                        help="photon collection efficiency")
    parser.add_argument("-ybwavelength", "--ybphotonwavelength", type=int, default=1389,
                        help="Yb emitted photon wavelength")
    parser.add_argument("-rb_telecom_wvln", "--rb_telecom_wavelength", type=int, default=1389,
                        help="Rb fiber wavelength after router-side AMZI/QFC conversion")
    parser.add_argument("-uw_output_wvln", "--uw_output_wavelength", type=int, default=1550,
                        help="uW transducer optical output wavelength before BSM-side QFC")
    parser.add_argument("-dtctor_dc", "--detectordarkcount", type=float, default=11.0,
                        help="detector dark count rate in Hz")
    parser.add_argument("-dtctor_eff", "--detectorefficiency", type=float, default=0.85,
                        help="BSM detector efficiency")
    parser.add_argument("-bsm_wvln", "--bsm_operating_wavelength", type=int, default=746,
                        help="photon wavelength used for transmon-atom BSMs")
    parser.add_argument("-atom_bsm_wvln", "--atom_bsm_wavelength", type=int, default=1389,
                        help="photon wavelength used for atom-atom BSMs")
    parser.add_argument("-qfc_eff", "--qfc_efficiency", type=float, default=1.0,
                        help="BSM-side QFC efficiency")
    parser.add_argument("-qfc_noise", "--qfc_noise", type=float, default=0.005,
                        help="BSM-side QFC noise probability")
    parser.add_argument("-uw_noise", "--transducer_noise", type=float, default=0.047,
                        help="transmon transducer noise")
    parser.add_argument("-uw_efficiency", "--transducer_efficiency", type=float, default=0.6,
                        help="transmon transducer efficiency")
    parser.add_argument("-uw_coherence", "--transmon_coherence_time", type=int, default=500_000_000, #.5ms
                        help="transmon coherence time in ps")
    parser.add_argument("-eta1", "--eta1converterefficiency", type=float, default=0.99,
                        help="Rb frequency conversion efficiency")
    parser.add_argument("-eta2", "--eta2converterefficiency", type=float, default=0.98,
                        help="Rb AMZI format conversion efficiency")
    parser.add_argument("-converter_noise", "--converternoise", type=float, default=0.005,
                        help="Rb frequency conversion noise probability")
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
    parser.add_argument("-log", "--logfile", type=str, default="tmp/het_four_node.log",
                        help="log file path")

    args = parser.parse_args()

    network_config = "config/line_4_het .json"
    network_topo = YbRouterNetTopo(network_config)
    tl = network_topo.get_timeline()

    configure_bsm_nodes(
        network_topo,
        args.detectorefficiency,
        args.detectordarkcount,
        args.bsm_operating_wavelength,
        args.atom_bsm_wavelength,
        args.ybphotonwavelength,
        args.rb_telecom_wavelength,
        args.uw_output_wavelength,
        args.qfc_efficiency,
        args.qfc_noise,
        args.eta2converterefficiency,
        args.binwidth,
        args.binseparation,
    )

    log.set_logger(__name__, tl, args.logfile)
    log.set_logger_level("WARNING")
    log.track_module("main_het_net_four_node_sim")
    log.track_module("generation")
    log.track_module("bsm")
    log.track_module("detector")
    log.track_module("memory")
    log.track_module("photon")
    log.track_module("custom_node")
    log.track_module("time_bin_bsm")
    log.track_module("optical_channel")
    log.track_module("apps")
    log.track_module("swapping")
    log.track_module("amziConverter")

    name_to_app = configure_router_nodes(
        network_topo,
        args.photoncollectionefficiency,
        args.ybphotonwavelength,
        args.transducer_efficiency,
        args.transducer_noise,
        args.transmon_coherence_time,
        args.rb_telecom_wavelength,
        args.uw_output_wavelength,
        args.eta1converterefficiency,
        args.eta2converterefficiency,
        args.converternoise,
        args.imaginglossprob,
        args.imageinterval,
        args.loadingtime,
        args.coolingtime,
        args.binwidth,
        args.binseparation,
    )

    delta = 20 * MILLISECOND
    total_time = 0

    tl.init()

    routers = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)
    node_init = routers[0]
    node_resp = routers[3]

    for i in range(args.numtrials):
        basis = "Z" if i % 2 == 1 else "X"
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        node_init.app.entanglement_time = None
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
        name_to_app[node_resp.name].basis = basis
        log.logger.warning(f"Starting four-node heterogeneous EG attempt {i + 1} at {tl.time}.")
        tl.run()

        if node_init.app.entanglement_time is None:
            raise RuntimeError(f"End-to-end entanglement attempt {i + 1} did not complete.")

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        actual_time = taken_time * 1e-12
        if actual_time < 0:
            raise ValueError("Negative entanglement generation time.")

        log.logger.warning(f"End-to-end entanglement num {i + 1} completed in {actual_time} seconds.")
        log.logger.warning(f"End-to-end entanglement num {i + 1} used {traversed_attempts} initiator attempts.")
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    x_trials = sum(node_init.app.meas_results[f"X_{i}{i}"] for i in range(1, 5))
    z_trials = sum(node_init.app.meas_results[f"Z_{i}{i}"] for i in range(1, 5))
    fid = None
    if x_trials > 0 and z_trials > 0:
        fid = node_init.app.get_fidelity(readout_fidelity0 * readout_fidelity1)
    attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts

    log.logger.warning(f"After {args.numtrials} successful end-to-end entanglement attempts, calculated fidelity={fid}")
    log.logger.warning(f"Average four-node end-to-end entanglement time is ~{total_time / args.numtrials}")
    log.logger.warning(f"{args.numtrials} end-to-end entanglement pairs were generated after {attempts} initiator attempts.")

    print(f"After {args.numtrials} successful end-to-end entanglement attempts, calculated fidelity={fid}")
    print(f"Average four-node end-to-end entanglement time: {total_time / args.numtrials} seconds")
    print(f"Log written to {args.logfile}")


if __name__ == "__main__":
    main()
