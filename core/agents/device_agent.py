# agents/device_agent.py
from core.kernel.device_manager import DeviceRegistry

class DeviceAgent:
    """
    Agent to manage device discovery and attach callbacks for data flow.
    """
    def __init__(self):
        self.registry = DeviceRegistry()
        # register built-in drivers
        from adapters.hardware.mock_device import MockDevice
        from adapters.hardware.openbci import OpenBCIDevice
        self.registry.register_driver('mock', MockDevice)
        self.registry.register_driver('openbci', OpenBCIDevice)

    def list(self):
        return self.registry.list_devices()

    async def create_and_start(self, key: str, **kwargs):
        device = self.registry.create(key, **kwargs)
        info = await device.initialize()
        await device.start_acquisition()
        return device, info