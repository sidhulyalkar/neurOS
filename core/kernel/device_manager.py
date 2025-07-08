# core/kernel/device_manager.py
from typing import Dict, Type
import uuid

class DeviceRegistry:
    """
    Manages discovery, registration, and lifecycle of BCIDevice instances.
    """
    def __init__(self):
        self._drivers: Dict[str, Type[BCIDevice]] = {}
        self._instances: Dict[str, BCIDevice] = {}

    def register_driver(self, key: str, driver_cls: Type[BCIDevice]) -> None:
        self._drivers[key] = driver_cls

    def create(self, key: str, **kwargs) -> BCIDevice:
        if key not in self._drivers:
            raise KeyError(f"Driver '{key}' not registered")
        device_id = str(uuid.uuid4())
        device = self._drivers[key](device_id=device_id, **kwargs)
        self._instances[device_id] = device
        return device

    def list_devices(self) -> Dict[str, BCIDevice]:
        return self._instances


# adapters/hardware/mock_device.py
import asyncio
import numpy as np
from core.kernel.device_driver import BCIDevice, DeviceState, DeviceInfo, SignalQuality

class MockDevice(BCIDevice):
    """
    Simulates a BCI device by emitting synthetic sine-wave data for testing pipelines.
    """
    def __init__(
        self,
        device_id: str,
        sample_rate: float = 256.0,
        channels: list = None,
        capabilities: list = None
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
            # Generate synthetic sine wave sample across channels
            sample = {ch: np.sin(2 * np.pi * 10 * self._t) for ch in self.channels}
            self._emit('data', sample)
            self._t += 1.0 / self.sample_rate
            await asyncio.sleep(1.0 / self.sample_rate)

    async def get_signal_quality(self) -> SignalQuality:
        # Return dummy stable quality
        return SignalQuality(
            snr_db=30.0,
            impedance_ohm={ch: 5.0 for ch in self.channels},
            battery_level=100.0
        )
