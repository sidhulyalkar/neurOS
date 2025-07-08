# adapters/hardware/openbci.py
from core.kernel.device_driver import BCIDevice, DeviceState, DeviceInfo, SignalQuality

class OpenBCIDevice(BCIDevice):
    """
    Adapter for OpenBCI boards (e.g., cyton). Implementation uses pyOpenBCI.
    """
    async def initialize(self) -> DeviceInfo:
        # TODO: integrate with pyOpenBCI
        self.state = DeviceState.INITIALIZING
        # fallback stub info
        info = DeviceInfo(
            manufacturer='OpenBCI',
            model='Cyton',
            serial_number='UNKNOWN',
            firmware_version='UNKNOWN',
            hardware_version='v3',
            capabilities=self.capabilities
        )
        self.state = DeviceState.CONNECTED
        return info

    async def start_acquisition(self) -> None:
        self.state = DeviceState.STREAMING
        # TODO: start pyOpenBCI stream and emit 'data'

    async def stop_acquisition(self) -> None:
        self.state = DeviceState.DISCONNECTED
        # TODO: stop the stream

    async def get_signal_quality(self) -> SignalQuality:
        # TODO: query impedance or other metrics
        return SignalQuality(snr_db=0.0, impedance_ohm={}, battery_level=None)
