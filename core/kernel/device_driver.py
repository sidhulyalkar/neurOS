# core/kernel/device_driver.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Callable, Optional
import asyncio

class DeviceState(Enum):
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    CONNECTED = auto()
    STREAMING = auto()
    ERROR = auto()
    DISCONNECTED = auto()

@dataclass
class DeviceInfo:
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    hardware_version: str
    capabilities: List[str]

@dataclass
class SignalQuality:
    snr_db: float
    impedance_ohm: Dict[str, float]
    battery_level: Optional[float]

class BCIDevice(ABC):
    """
    Abstract base class for all BCI hardware devices.
    """
    def __init__(
        self,
        device_id: str,
        sample_rate: float,
        channels: List[str],
        capabilities: List[str]
    ):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.capabilities = capabilities
        self.state = DeviceState.UNINITIALIZED
        self._callbacks: Dict[str, List[Callable[[Any], None]]] = {}
        self._stream_task: Optional[asyncio.Task] = None

    @abstractmethod
    async def initialize(self) -> DeviceInfo:
        pass

    @abstractmethod
    async def start_acquisition(self) -> None:
        pass

    @abstractmethod
    async def stop_acquisition(self) -> None:
        pass

    @abstractmethod
    async def get_signal_quality(self) -> SignalQuality:
        pass

    def on(self, event_type: str, callback: Callable[[Any], None]) -> None:
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def _emit(self, event_type: str, payload: Any) -> None:
        for cb in self._callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(payload))
                else:
                    cb(payload)
            except Exception as e:
                self._emit('error', e)