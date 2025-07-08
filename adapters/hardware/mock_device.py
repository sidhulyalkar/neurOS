# adapters/hardware/mock_device.py
import asyncio
import numpy as np
from typing import List
from core.kernel.device_driver import BCIDevice, DeviceState, DeviceInfo, SignalQuality

class MockDevice(BCIDevice):
    """
    Simulates a BCI device by emitting synthetic sine-wave data for testing.
    """
    def __init__(
        self,
        device_id: str,
        sample_rate: float = 256.0,
        channels: List[str] = None,
        capabilities: List[str] = None
    ):
        super().__init__(
            device_id=device_id,
            sample_rate=sample_rate,
            channels=channels or ['Cz'],
            capabilities=capabilities or ['EEG']
        )
        self._running = False
        self._t = 0.0

    async def initialize(self) -> DeviceInfo:
        self.state = DeviceState.CONNECTED
        return DeviceInfo(
            manufacturer='MockCorp',
            model='MockAlpha',
            serial_number='MOCK1234',
            firmware_version='0.1',
            hardware_version='0.1',
            capabilities=self.capabilities
        )

    async def start_acquisition(self) -> None:
        self.state = DeviceState.STREAMING
        self._running = True
        self._stream_task = asyncio.create_task(self._stream_loop())

    async def stop_acquisition(self) -> None:
        self._running = False
        if self._stream_task:
            await self._stream_task
        self.state = DeviceState.DISCONNECTED

    async def _stream_loop(self):
        while self._running:
            sample = {ch: np.sin(2 * np.pi * 10 * self._t) for ch in self.channels}
            self._emit('data', sample)
            self._t += 1.0 / self.sample_rate
            await asyncio.sleep(1.0 / self.sample_rate)

    async def get_signal_quality(self) -> SignalQuality:
        return SignalQuality(
            snr_db=30.0,
            impedance_ohm={ch: 5.0 for ch in self.channels},
            battery_level=100.0
        )