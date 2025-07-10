# neuros/testing/synthetic.py
"""
Synthetic Testing System for neurOS
Generate realistic BCI data and test all components without hardware
"""

import numpy as np
import asyncio
import time
from typing import Dict, Any, List
from dataclasses import dataclass
import logging

@dataclass
class SyntheticEEGConfig:
    """Configuration for synthetic EEG generation"""
    channels: int = 64
    sample_rate: int = 250  # Hz
    duration: float = 10.0  # seconds
    noise_level: float = 0.1
    add_artifacts: bool = True
    add_motor_imagery: bool = True

class SyntheticEEGGenerator:
    """Generate realistic synthetic EEG data"""
    
    def __init__(self, config: SyntheticEEGConfig):
        self.config = config
        self.logger = logging.getLogger("neurOS.testing.eeg")
        
        # Standard 10-20 electrode positions (simplified)
        self.electrode_names = [
            'Fp1', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6',
            'T7', 'C3', 'Cz', 'C4', 'T8', 'TP9', 'CP5', 'CP1', 'CP2', 'CP6', 'TP10',
            'P7', 'P3', 'Pz', 'P4', 'P8', 'PO9', 'O1', 'Oz', 'O2', 'PO10'
        ]
        
        # Extend with numbered channels if needed
        while len(self.electrode_names) < config.channels:
            self.electrode_names.append(f'Ch{len(self.electrode_names) + 1}')
    
    def generate_background_eeg(self, samples: int) -> np.ndarray:
        """Generate background EEG with typical frequency bands"""
        data = np.zeros((self.config.channels, samples))
        t = np.linspace(0, samples / self.config.sample_rate, samples)
        
        for ch in range(self.config.channels):
            # Alpha band (8-12 Hz) - prominent in occipital channels
            alpha_power = 2.0 if ch >= 28 else 1.0  # Higher in O1, Oz, O2
            data[ch] += alpha_power * np.sin(2 * np.pi * 10 * t + np.random.random() * 2 * np.pi)
            
            # Beta band (13-30 Hz) - motor cortex
            beta_power = 1.5 if 12 <= ch <= 16 else 0.8  # Higher in motor areas
            data[ch] += beta_power * np.sin(2 * np.pi * 20 * t + np.random.random() * 2 * np.pi)
            
            # Theta band (4-7 Hz)
            data[ch] += 0.5 * np.sin(2 * np.pi * 6 * t + np.random.random() * 2 * np.pi)
            
            # Gamma band (30-100 Hz) - low amplitude
            data[ch] += 0.2 * np.sin(2 * np.pi * 40 * t + np.random.random() * 2 * np.pi)
            
            # Noise
            data[ch] += self.config.noise_level * np.random.randn(samples)
        
        return data
    
    def add_motor_imagery_erp(self, data: np.ndarray, event_times: List[float]) -> np.ndarray:
        """Add motor imagery event-related potentials"""
        motor_channels = [12, 13, 14]  # C3, Cz, C4
        
        for event_time in event_times:
            event_sample = int(event_time * self.config.sample_rate)
            
            # ERP duration: 1 second
            erp_duration = int(1.0 * self.config.sample_rate)
            
            if event_sample + erp_duration < data.shape[1]:
                t_erp = np.linspace(0, 1, erp_duration)
                
                # Simulate mu rhythm desynchronization (beta ERD)
                for ch in motor_channels:
                    # Negative peak around 100ms, positive around 300ms
                    erp = -3.0 * np.exp(-((t_erp - 0.1) / 0.05)**2)  # N100
                    erp += 2.0 * np.exp(-((t_erp - 0.3) / 0.1)**2)   # P300
                    erp += -1.5 * np.exp(-((t_erp - 0.6) / 0.15)**2) # Late negative
                    
                    data[ch, event_sample:event_sample + erp_duration] += erp
        
        return data
    
    def add_artifacts(self, data: np.ndarray) -> np.ndarray:
        """Add realistic artifacts (eye blinks, muscle, etc.)"""
        samples = data.shape[1]
        
        # Eye blinks (affects frontal channels)
        frontal_channels = [0, 1]  # Fp1, Fp2
        blink_times = np.random.poisson(0.3, int(samples / self.config.sample_rate))
        
        for i, blinks in enumerate(blink_times):
            for _ in range(blinks):
                blink_start = np.random.randint(i * self.config.sample_rate, 
                                              min((i + 1) * self.config.sample_rate, samples - 50))
                blink_duration = 50  # ~200ms at 250Hz
                
                # Blink artifact shape
                t_blink = np.linspace(0, 1, blink_duration)
                blink_shape = 100 * np.exp(-((t_blink - 0.5) / 0.2)**2)
                
                for ch in frontal_channels:
                    if blink_start + blink_duration < samples:
                        data[ch, blink_start:blink_start + blink_duration] += blink_shape
        
        # 50/60 Hz power line noise
        t = np.linspace(0, samples / self.config.sample_rate, samples)
        power_line = 0.5 * np.sin(2 * np.pi * 50 * t)  # 50 Hz
        for ch in range(self.config.channels):
            data[ch] += power_line * (0.5 + 0.5 * np.random.random())
        
        return data
    
    def generate_session(self) -> Dict[str, Any]:
        """Generate a complete synthetic EEG session"""
        total_samples = int(self.config.duration * self.config.sample_rate)
        
        # Generate background EEG
        data = self.generate_background_eeg(total_samples)
        
        # Add motor imagery events
        if self.config.add_motor_imagery:
            event_times = np.random.uniform(1, self.config.duration - 1, 5)  # 5 events
            data = self.add_motor_imagery_erp(data, event_times)
        
        # Add artifacts
        if self.config.add_artifacts:
            data = self.add_artifacts(data)
        
        # Create timestamps
        timestamps = np.linspace(0, self.config.duration, total_samples)
        
        return {
            'data': data,
            'timestamps': timestamps,
            'sample_rate': self.config.sample_rate,
            'channels': self.config.channels,
            'electrode_names': self.electrode_names[:self.config.channels],
            'duration': self.config.duration,
            'events': event_times if self.config.add_motor_imagery else []
        }

class SyntheticDeviceSimulator:
    """Simulate BCI hardware device for testing"""
    
    def __init__(self, device_type: str = "openbci_cyton"):
        self.device_type = device_type
        self.is_connected = False
        self.is_streaming = False
        self.sample_count = 0
        
        # Device-specific configs
        self.configs = {
            'openbci_cyton': {'channels': 8, 'sample_rate': 250},
            'emotiv_epoc': {'channels': 14, 'sample_rate': 128},
            'biosemi_64': {'channels': 64, 'sample_rate': 512}
        }
        
        self.config = self.configs.get(device_type, self.configs['openbci_cyton'])
        self.eeg_generator = SyntheticEEGGenerator(SyntheticEEGConfig(
            channels=self.config['channels'],
            sample_rate=self.config['sample_rate']
        ))
    
    async def connect(self) -> bool:
        """Simulate device connection"""
        await asyncio.sleep(1)  # Connection delay
        self.is_connected = True
        return True
    
    async def start_streaming(self, callback=None) -> bool:
        """Start streaming synthetic data"""
        if not self.is_connected:
            return False
        
        self.is_streaming = True
        
        # Generate continuous data
        session_data = self.eeg_generator.generate_session()
        data = session_data['data']
        
        # Stream data in real-time chunks
        chunk_size = int(self.config['sample_rate'] * 0.04)  # 40ms chunks
        
        for i in range(0, data.shape[1], chunk_size):
            if not self.is_streaming:
                break
            
            chunk = data[:, i:i + chunk_size]
            timestamp = time.time()
            
            packet = {
                'timestamp': timestamp,
                'sample_number': self.sample_count,
                'data': chunk,
                'device_type': self.device_type
            }
            
            if callback:
                await callback(packet)
            
            self.sample_count += chunk.shape[1]
            await asyncio.sleep(0.04)  # Real-time delay
        
        return True
    
    async def stop_streaming(self):
        """Stop streaming"""
        self.is_streaming = False
    
    async def disconnect(self):
        """Disconnect device"""
        self.is_streaming = False
        self.is_connected = False

# Add CLI commands for synthetic testing
def add_synthetic_test_commands():
    """Add synthetic testing commands to CLI"""
    
    @click.group()
    def test():
        """Synthetic testing commands"""
        pass
    
    @test.command('eeg')
    @click.option('--channels', default=32, help='Number of channels')
    @click.option('--duration', default=10, help='Duration in seconds')
    @click.option('--sample-rate', default=250, help='Sample rate in Hz')
    @click.option('--output', help='Save data to file')
    def test_eeg(channels, duration, sample_rate, output):
        """Generate synthetic EEG data"""
        click.echo(f"🧠 Generating {duration}s of {channels}-channel EEG at {sample_rate}Hz...")
        
        config = SyntheticEEGConfig(
            channels=channels,
            duration=duration,
            sample_rate=sample_rate
        )
        
        generator = SyntheticEEGGenerator(config)
        session = generator.generate_session()
        
        click.echo(f"✅ Generated {session['data'].shape[1]} samples")
        click.echo(f"📊 Data shape: {session['data'].shape}")
        click.echo(f"⚡ Events: {len(session['events'])} motor imagery events")
        
        if output:
            np.savez(output, **session)
            click.echo(f"💾 Saved to {output}")
    
    @test.command('device')
    @click.option('--device', default='openbci_cyton', 
                  type=click.Choice(['openbci_cyton', 'emotiv_epoc', 'biosemi_64']))
    @click.option('--duration', default=10, help='Streaming duration')
    def test_device(device, duration):
        """Test synthetic device streaming"""
        
        async def run_test():
            click.echo(f"🔌 Testing {device} simulation...")
            
            simulator = SyntheticDeviceSimulator(device)
            
            # Connection test
            success = await simulator.connect()
            click.echo(f"📡 Connection: {'✅' if success else '❌'}")
            
            # Streaming test
            packet_count = 0
            
            async def data_callback(packet):
                nonlocal packet_count
                packet_count += 1
                if packet_count % 25 == 0:  # Every second
                    click.echo(f"📊 Received {packet_count} packets, "
                             f"Latest shape: {packet['data'].shape}")
            
            click.echo(f"🔄 Starting {duration}s stream...")
            await asyncio.wait_for(
                simulator.start_streaming(data_callback), 
                timeout=duration + 1
            )
            
            await simulator.disconnect()
            click.echo(f"✅ Test completed. Total packets: {packet_count}")
        
        asyncio.run(run_test())
    
    @test.command('realtime')
    @click.option('--latency-target', default=50, help='Target latency (ms)')
    @click.option('--duration', default=30, help='Test duration (seconds)')
    def test_realtime(latency_target, duration):
        """Test real-time processing with synthetic data"""
        
        async def run_realtime_test():
            click.echo(f"⚡ Testing real-time processing (target: {latency_target}ms)")
            
            # Simulate real-time processor
            latencies = []
            
            for i in range(duration * 10):  # 10 Hz test
                start_time = time.perf_counter()
                
                # Simulate processing
                data = np.random.randn(32, 25)  # 32 channels, 100ms of data
                processed = data * 0.95  # Simple processing
                
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
                
                if i % 10 == 0:
                    avg_latency = np.mean(latencies[-10:])
                    click.echo(f"📈 Sample {i}: {avg_latency:.2f}ms avg latency")
                
                await asyncio.sleep(0.1)  # 10 Hz
            
            # Results
            avg_latency = np.mean(latencies)
            max_latency = np.max(latencies)
            click.echo(f"\n📊 Results:")
            click.echo(f"   Average latency: {avg_latency:.2f}ms")
            click.echo(f"   Maximum latency: {max_latency:.2f}ms")
            click.echo(f"   Target met: {'✅' if avg_latency <= latency_target else '❌'}")
        
        asyncio.run(run_realtime_test())
    
    return test

# Example usage
if __name__ == "__main__":
    # Test synthetic EEG generation
    config = SyntheticEEGConfig(channels=32, duration=5.0)
    generator = SyntheticEEGGenerator(config)
    session = generator.generate_session()
    
    print(f"Generated EEG data: {session['data'].shape}")
    print(f"Events: {len(session['events'])}")
    
    # Test device simulation
    async def test_device_sim():
        simulator = SyntheticDeviceSimulator('openbci_cyton')
        await simulator.connect()
        
        packet_count = 0
        async def callback(packet):
            nonlocal packet_count
            packet_count += 1
            print(f"Packet {packet_count}: {packet['data'].shape}")
        
        await asyncio.wait_for(simulator.start_streaming(callback), timeout=3)
        print(f"Total packets: {packet_count}")
    
    # asyncio.run(test_device_sim())