'''
This file is to try and do realistic simulation of entanglement generation
between two single-atom Rb nodes. Outlined/modeled from main_yb_yb_EG_sim.py
'''

from sequence.utils import log
from yb_router_net_topo import YbRouterNetTopo
from sequence.constants import MILLISECOND, SECOND
from apps import HetRequestApp
from memory import MemoryArray
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pce', '--photoncollectionefficiency', type=float, default=0.5,
                        help='efficiency of Rb photon collection into fiber') # we have data from paper here TODO ask Caitao which value to use 
    parser.add_argument('-n', '--numtrials', type=int, default=1000,
                        help='number of entangled pairs to generate')
    parser.add_argument('-dtctor_dc', '--detectordarkcount', type=float, default=11.0,
                        help='dark count rate, in Hz, for the detector in the BSM') # TODO ask Caitao about this one coppied over from Hayden 
    parser.add_argument('-dtctor_eff', '--detectorefficiency', type=float, default=0.8,
                        help='efficiency for the detector in the BSM') #TODO again ask Caitao just used Hayden value for now
    parser.add_argument('-bsm_wvln', '--bsm_operating_wavelength', type=int, default=1389,
                        help='photon wavelength the BSM receives after Rb conversion') #think thi6s is good after conversion recieve this wavelength
    parser.add_argument('-eta1', '--eta1converterefficiency', type=float, default=0.99,
                        help='Rb frequency conversion efficiency')
    parser.add_argument('-eta2', '--eta2converterefficiency', type=float, default=0.98,
                        help='Rb format conversion efficiency')
    parser.add_argument('-converter_noise', '--converternoise', type=float, default=0.005,
                        help='Rb frequency conversion noise probability') 
    parser.add_argument('-image_loss', '--imaginglossprob', type=float, default=0.095, 
                        help='probability imaging finds the Rb atom lost')
    parser.add_argument('-image_interval', '--imageinterval', type=int, default=20,
                        help='number of excitation cycles between imaging checks')
    parser.add_argument('-cool', '--coolingtime', type=int, default=1_000_000_000,
                        help='Rb cooling time in ps')
    parser.add_argument('-load', '--loadingtime', type=int, default=10_000_000,
                        help='Rb atom loading time in ps')
    parser.add_argument('-bwidth', '--binwidth', type=int, default=520_000,
                        help='temporal width of the converted time bin') 
    parser.add_argument('-bsep', '--binseparation', type=int, default=2_800_000,
                        help='temporal separation between early and late converted bins') 
    parser.add_argument('-log', '--logfile', type=str, default='tmp/rb_rb.log',
                        help='log file path')

    args = parser.parse_args()
    photon_collection_efficiency = args.photoncollectionefficiency
    n = args.numtrials
    detector_dark_count = args.detectordarkcount
    detector_efficiency = args.detectorefficiency
    bsm_operating_wavelength = args.bsm_operating_wavelength
    eta1_converter_efficiency = args.eta1converterefficiency
    eta2_converter_efficiency = args.eta2converterefficiency
    converter_noise = args.converternoise
    imaging_loss_prob = args.imaginglossprob
    image_interval = args.imageinterval
    #max_cycles_before_loss = args.maxcyclesbeforeloss
    cooling_time = args.coolingtime
    loading_time = args.loadingtime
    bin_width = args.binwidth
    bin_separation = args.binseparation
    log_filename = args.logfile
   
    network_config = 'config/linearRbRb.json'   
    network_topo = YbRouterNetTopo(network_config)
    tl = network_topo.get_timeline()
    bsm_hardware_name = 'HetTimeBinBSM'

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
        bsm.update_detectors_params('efficiency', detector_efficiency)
        bsm.update_detectors_params('dark_count', detector_dark_count)

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

    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('WARNING')
    log.track_module('main_rb_rb_EG_sim')
    log.track_module('generation')
    log.track_module('bsm')
    log.track_module('detector')
    log.track_module('memory')
    log.track_module('photon')
    log.track_module('apps') #for debugging purposes can remove later 
    log.track_module('custom_node')
    log.track_module('time_bin_bsm')
    log.track_module('optical_channel')
    log.track_module('amziConverter')

    total_time = 0
    name_to_app = {}

    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER): #had way more memory paramaters so added them all here for now TODO tons of redudancy here because already set earlier so can clean this up a ton
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
            #mem.max_cycles_before_loss = max_cycles_before_loss
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
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)

    delta = 20 * MILLISECOND
    tl.init()

    node_init = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[0]
    node_resp = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[1]

    for i in range(n):
        basis = "Z" if i % 2 == 1 else "X"
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
            node.app.last_trap_time = beginning - node.app.time_in_trap
        name_to_app[node_init.name].start(node_resp.name, beginning + delta, beginning + 10000 * SECOND, 1, 0.1, basis)
        name_to_app[node_resp.name].basis = basis
        log.logger.warning("Starting Rb to Rb EG attempt at " + str(tl.time) + '.')
        tl.run()

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        actual_time = taken_time * (10 ** -12)
        if actual_time < 0:
            raise ValueError('neg actual time')
        log.logger.warning(f'Entanglement num {i + 1} completed in {actual_time} seconds.')
        log.logger.warning(f'Entanglement num {i + 1} took {traversed_attempts} attempts.')
        total_time += actual_time

    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity_product = readout_fidelity0 * readout_fidelity1
    fid = node_init.app.get_fidelity(readout_fidelity_product)

    log.logger.warning(f'pce:{photon_collection_efficiency}')
    log.logger.warning(f'loading_time:{loading_time}')
    log.logger.warning(f'loading_time_ms:{loading_time * 1e-9}')
    log.logger.warning(f'cooling_time:{cooling_time}')
    log.logger.warning(f'cooling_time_ms:{cooling_time * 1e-9}')

    log.logger.warning(f'After {n} successful entanglement attempts, calculated fidelity ={fid}')
    log.logger.warning(f'Average ent time is ~{total_time / n}')
    attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
    log.logger.warning(f'{n} entanglement pairs were generated after {attempts} attempts; generation success rate: {n / attempts}')


if __name__ == "__main__":
    main()
