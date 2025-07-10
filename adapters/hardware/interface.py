# adapters/hardware/interface.py
"""
Universal Hardware Interface System for neurOS
Supports multiple BCI hardware platforms with unified API
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import numpy as np
import yaml
import threading
import queue

class HardwareType(Enum):
    EEG = "eeg"
    ECOG = "ecog"
    FNIRS = "fnirs"
    HYBRID = "hybrid"

class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"

@dataclass
class HardwareSpec:
    """Hardware specification configuration"""
    name: str
    hardware_type: HardwareType
    channels: int
    sample_rate: int
    resolution_bits: int
    impedance_check: bool = True
    trigger_support: bool = True
    wireless: bool = False
    battery_monitor: bool = False
    firmware_version: str = "unknown"

@dataclass
class ChannelInfo:
    """Information about a single channel"""
    index: int
    name: str
    enabled: bool = True
    impedance_kohm: float = 0.0
    gain: float = 1.0
    offset: float = 0.0
    location: str = ""
    signal_type: str = "eeg"

@dataclass
class DataPacket:
    """Standard data packet format"""
    timestamp: float
    sample_number: int
    channel_data: np.ndarray
    trigger_data: Optional[np.ndarray] = None
    impedance_data: Optional[np.ndarray] = None
    battery_level: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseHardwareInterface(ABC):
    """Base class for all hardware interfaces"""
    
    def __init__(self, spec: HardwareSpec, config: Dict[str, Any] = None):
        self.spec = spec
        self.config = config or {}
        self.logger = logging.getLogger(f"neurOS.hardware.{spec.name}")
        
        self.status = ConnectionStatus.DISCONNECTED
        self.channels: List[ChannelInfo] = []
        self.is_streaming = False
        self.data_callbacks: List[Callable] = []
        
        # Performance tracking
        self.packets_received = 0
        self.packets_dropped = 0
        self.last_packet_time = 0
        
        # Initialize channels
        for i in range(spec.channels):
            self.channels.append(ChannelInfo(
                index=i,
                name=f"Ch{i+1}",
                location=f"electrode_{i+1}"
            ))
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to hardware device"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from hardware device"""
        pass
    
    @abstractmethod
    async def start_streaming(self) -> bool:
        """Start data acquisition"""
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> bool:
        """Stop data acquisition"""
        pass
    
    @abstractmethod
    async def check_impedances(self) -> Dict[int, float]:
        """Check electrode impedances"""
        pass
    
    @abstractmethod
    async def send_trigger(self, trigger_value: int) -> bool:
        """Send trigger/marker"""
        pass
    
    def add_data_callback(self, callback: Callable[[DataPacket], None]):
        """Add callback for incoming data"""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[DataPacket], None]):
        """Remove data callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    async def _notify_callbacks(self, packet: DataPacket):
        """Notify all callbacks of new data"""
        for callback in self.data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(packet)
                else:
                    callback(packet)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get device status"""
        return {
            'name': self.spec.name,
            'type': self.spec.hardware_type.value,
            'status': self.status.value,
            'channels': len(self.channels),
            'sample_rate': self.spec.sample_rate,
            'streaming': self.is_streaming,
            'packets_received': self.packets_received,
            'packets_dropped': self.packets_dropped,
            'data_rate': self.packets_received / max(1, time.time() - self.last_packet_time) if self.last_packet_time else 0
        }

class OpenBCIInterface(BaseHardwareInterface):
    """Interface for OpenBCI devices (Cyton, Ganglion, etc.)"""
    
    def __init__(self, spec: HardwareSpec, config: Dict[str, Any] = None):
        super().__init__(spec, config)
        self.serial_port = config.get('serial_port', '/dev/ttyUSB0')
        self.board = None
        self.streaming_task = None
        
    async def connect(self) -> bool:
        """Connect to OpenBCI board"""
        try:
            self.status = ConnectionStatus.CONNECTING
            
            # Import OpenBCI library (would need to be installed)
            # from openbci_stream import OpenBCIBoard
            
            # Simulate connection for demo
            await asyncio.sleep(1)
            
            self.status = ConnectionStatus.CONNECTED
            self.logger.info(f"Connected to OpenBCI at {self.serial_port}")
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from OpenBCI board"""
        try:
            if self.is_streaming:
                await self.stop_streaming()
            
            self.status = ConnectionStatus.DISCONNECTED
            self.logger.info("Disconnected from OpenBCI")
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnect failed: {e}")
            return False
    
    async def start_streaming(self) -> bool:
        """Start data streaming"""
        if self.status != ConnectionStatus.CONNECTED:
            self.logger.error("Device not connected")
            return False
        
        try:
            self.is_streaming = True
            self.status = ConnectionStatus.STREAMING
            
            # Start streaming task
            self.streaming_task = asyncio.create_task(self._streaming_loop())
            
            self.logger.info("Started data streaming")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def stop_streaming(self) -> bool:
        """Stop data streaming"""
        try:
            self.is_streaming = False
            
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass
            
            self.status = ConnectionStatus.CONNECTED
            self.logger.info("Stopped data streaming")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop streaming: {e}")
            return False
    
    async def _streaming_loop(self):
        """Main streaming loop"""
        sample_number = 0
        
        while self.is_streaming:
            try:
                # Simulate data acquisition
                timestamp = time.time()
                channel_data = np.random.randn(self.spec.channels) * 50  # Simulate EEG data
                
                packet = DataPacket(
                    timestamp=timestamp,
                    sample_number=sample_number,
                    channel_data=channel_data,
                    metadata={'source': 'openbci_simulation'}
                )
                
                await self._notify_callbacks(packet)
                
                self.packets_received += 1
                self.last_packet_time = timestamp
                sample_number += 1
                
                # Wait for next sample
                await asyncio.sleep(1.0 / self.spec.sample_rate)
                
            except Exception as e:
                self.logger.error(f"Streaming error: {e}")
                self.packets_dropped += 1
    
    async def check_impedances(self) -> Dict[int, float]:
        """Check electrode impedances"""
        # Simulate impedance check
        impedances = {}
        for i in range(self.spec.channels):
            impedances[i] = np.random.uniform(1, 50)  # kOhm
        
        self.logger.info("Impedance check completed")
        return impedances
    
    async def send_trigger(self, trigger_value: int) -> bool:
        """Send trigger to OpenBCI"""
        try:
            # In real implementation, send trigger command to board
            self.logger.info(f"Trigger sent: {trigger_value}")
            return True
        except Exception as e:
            self.logger.error(f"Trigger failed: {e}")
            return False

class EmotivInterface(BaseHardwareInterface):
    """Interface for Emotiv devices (EPOC, Insight, etc.)"""
    
    def __init__(self, spec: HardwareSpec, config: Dict[str, Any] = None):
        super().__init__(spec, config)
        self.client_id = config.get('client_id', '')
        self.client_secret = config.get('client_secret', '')
        
    async def connect(self) -> bool:
        """Connect to Emotiv device"""
        try:
            self.status = ConnectionStatus.CONNECTING
            
            # Simulate Emotiv connection
            await asyncio.sleep(2)
            
            self.status = ConnectionStatus.CONNECTED
            self.logger.info("Connected to Emotiv device")
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.logger.error(f"Emotiv connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Emotiv device"""
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    async def start_streaming(self) -> bool:
        """Start Emotiv data streaming"""
        self.is_streaming = True
        self.status = ConnectionStatus.STREAMING
        
        # Start streaming task with Emotiv-specific implementation
        self.streaming_task = asyncio.create_task(self._emotiv_streaming_loop())
        
        return True
    
    async def stop_streaming(self) -> bool:
        """Stop Emotiv streaming"""
        self.is_streaming = False
        if self.streaming_task:
            self.streaming_task.cancel()
        return True
    
    async def _emotiv_streaming_loop(self):
        """Emotiv-specific streaming loop"""
        sample_number = 0
        
        while self.is_streaming:
            # Simulate Emotiv data with different characteristics
            timestamp = time.time()
            channel_data = np.random.randn(self.spec.channels) * 30
            
            packet = DataPacket(
                timestamp=timestamp,
                sample_number=sample_number,
                channel_data=channel_data,
                battery_level=np.random.uniform(0.7, 1.0),  # Emotiv has battery
                metadata={'source': 'emotiv_simulation'}
            )
            
            await self._notify_callbacks(packet)
            self.packets_received += 1
            sample_number += 1
            
            await asyncio.sleep(1.0 / self.spec.sample_rate)
    
    async def check_impedances(self) -> Dict[int, float]:
        """Emotiv impedance check"""
        # Emotiv has different impedance characteristics
        impedances = {}
        for i in range(self.spec.channels):
            impedances[i] = np.random.uniform(0.5, 10)  # Lower impedances
        return impedances
    
    async def send_trigger(self, trigger_value: int) -> bool:
        """Emotiv trigger (may not be supported on all models)"""
        self.logger.warning("Triggers may not be supported on this Emotiv model")
        return False

class HardwareManager:
    """Manages multiple hardware devices"""
    
    def __init__(self):
        self.devices: Dict[str, BaseHardwareInterface] = {}
        self.logger = logging.getLogger("neurOS.hardware_manager")
        
    def register_device(self, device_id: str, device: BaseHardwareInterface):
        """Register a hardware device"""
        self.devices[device_id] = device
        self.logger.info(f"Registered device: {device_id}")
    
    async def connect_device(self, device_id: str) -> bool:
        """Connect to specific device"""
        if device_id not in self.devices:
            self.logger.error(f"Unknown device: {device_id}")
            return False
        
        return await self.devices[device_id].connect()
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect specific device"""
        if device_id not in self.devices:
            return False
        
        return await self.devices[device_id].disconnect()
    
    async def start_streaming(self, device_id: str) -> bool:
        """Start streaming from device"""
        if device_id not in self.devices:
            return False
        
        return await self.devices[device_id].start_streaming()
    
    async def stop_streaming(self, device_id: str) -> bool:
        """Stop streaming from device"""
        if device_id not in self.devices:
            return False
        
        return await self.devices[device_id].stop_streaming()
    
    def get_device_status(self, device_id: str = None) -> Dict[str, Any]:
        """Get status of device(s)"""
        if device_id:
            if device_id in self.devices:
                return self.devices[device_id].get_status()
            return {}
        
        # Return status of all devices
        status = {}
        for dev_id, device in self.devices.items():
            status[dev_id] = device.get_status()
        
        return status
    
    async def auto_discover(self) -> List[str]:
        """Auto-discover available devices"""
        discovered = []
        
        # Simulate device discovery
        self.logger.info("Scanning for BCI devices...")
        await asyncio.sleep(2)
        
        # Mock discovery results
        mock_devices = [
            ("openbci_cyton", OpenBCIInterface, {
                'name': 'OpenBCI Cyton',
                'hardware_type': HardwareType.EEG,
                'channels': 8,
                'sample_rate': 250,
                'resolution_bits': 24
            }),
            ("emotiv_epoc", EmotivInterface, {
                'name': 'Emotiv EPOC',
                'hardware_type': HardwareType.EEG,
                'channels': 14,
                'sample_rate': 128,
                'resolution_bits': 16
            })
        ]
        
        for device_id, interface_class, spec_dict in mock_devices:
            try:
                spec = HardwareSpec(**spec_dict)
                device = interface_class(spec)
                self.register_device(device_id, device)
                discovered.append(device_id)
                
            except Exception as e:
                self.logger.error(f"Failed to create device {device_id}: {e}")
        
        self.logger.info(f"Discovered {len(discovered)} devices: {discovered}")
        return discovered

# Configuration loader for hardware profiles
def load_hardware_profile(profile_path: str) -> HardwareSpec:
    """Load hardware specification from YAML file"""
    with open(profile_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return HardwareSpec(
        name=config['name'],
        hardware_type=HardwareType(config['type']),
        channels=config['channels'],
        sample_rate=config['sample_rate'],
        resolution_bits=config.get('resolution_bits', 24),
        impedance_check=config.get('impedance_check', True),
        trigger_support=config.get('trigger_support', True),
        wireless=config.get('wireless', False),
        battery_monitor=config.get('battery_monitor', False),
        firmware_version=config.get('firmware_version', 'unknown')
    )

# Example usage and testing
if __name__ == "__main__":
    async def test_hardware_interface():
        # Create hardware manager
        manager = HardwareManager()
        
        # Auto-discover devices
        devices = await manager.auto_discover()
        
        if devices:
            device_id = devices[0]
            
            # Connect to first device
            print(f"Connecting to {device_id}...")
            success = await manager.connect_device(device_id)
            
            if success:
                print("Connected successfully!")
                
                # Check status
                status = manager.get_device_status(device_id)
                print(f"Device status: {status}")
                
                # Start streaming
                print("Starting data stream...")
                await manager.start_streaming(device_id)
                
                # Let it stream for a few seconds
                await asyncio.sleep(5)
                
                # Stop streaming
                await manager.stop_streaming(device_id)
                await manager.disconnect_device(device_id)
                
                print("Test completed successfully!")
        else:
            print("No devices discovered")
    
    # Run test
    asyncio.run(test_hardware_interface())