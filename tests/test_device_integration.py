# tests/test_device_integration.py
import asyncio
import pytest
from adapters.hardware.mock_device import MockDevice

def test_mock_device_stream_and_quality():
    """
    Synchronous test invoking the MockDevice via explicit asyncio event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    device = MockDevice(device_id='test', sample_rate=10.0)
    info = loop.run_until_complete(device.initialize())
    assert info.manufacturer == 'MockCorp'
    data_samples = []

    def on_data(sample):
        data_samples.append(sample)

    device.on('data', on_data)
    loop.run_until_complete(device.start_acquisition())
    # collect for 0.2 seconds
    loop.run_until_complete(asyncio.sleep(0.2))
    loop.run_until_complete(device.stop_acquisition())

    assert len(data_samples) >= 1

    quality = loop.run_until_complete(device.get_signal_quality())
    assert quality.snr_db == 30.0
    assert 'Cz' in quality.impedance_ohm
    
    loop.close()