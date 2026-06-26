from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from photon import HetPhoton


class AmziConverter(Entity):
    """
    Polarization to time-bin format converter
    This models the AMZI format conversion from paper (one Caitao sent on slack gotta paste here). 
    By default it is disabled and simply passes photons through, which keeps existing Yb and uW paths unchanged unless a
    simulation explicitly enables the converter.
    """

    def __init__(self, name: str, timeline: Timeline, input_encoding: str = "polarization", output_encoding: str = "rb_time_bin", efficiency: float = 1.0, bin_width: int = None, bin_separation: int = None, enabled: bool = False):
        super().__init__(name, timeline)
        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.efficiency = efficiency
        self.bin_width = bin_width
        self.bin_separation = bin_separation
        self.enabled = enabled

    def init(self) -> None:
        pass

    def get(self, photon: HetPhoton):
        encoding_name = None
        if photon.encoding_type is not None:
            encoding_name = photon.encoding_type.get("name")

        if self.enabled and encoding_name == self.input_encoding: #ensures that input is encoding and also has to be enabled
            photon.encoding_type = {"name": self.output_encoding, "keep_photon": True}
            photon.add_loss(1 - self.efficiency)


        self._receivers[0].get(photon)
