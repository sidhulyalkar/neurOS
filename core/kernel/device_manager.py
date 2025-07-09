# core/kernel/device_manager.py
from typing import Dict, Type
from core.kernel.device_driver import BCIDevice
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
