# core/signals/bandpass_filter.py
from typing import Dict, Any
import numpy as np
from scipy.signal import butter, lfilter
from core.signals.pipeline import SignalProcessor

class BandpassFilter(SignalProcessor[Dict[str, float]]):
    """
    SignalProcessor implementation for a band-pass filter on channel data.
    """
    def __init__(self, low: float, high: float, fs: float, order: int = 5):
        """
        Initialize a BandpassFilter object.

        Parameters
        ----------
        low : float
            lower bound of frequency range to keep
        high : float
            upper bound of frequency range to keep
        fs : float
            sampling rate of the signal
        order : int, optional
            order of the Butterworth filter, by default 5

        """
        # Design Butterworth bandpass filter
        nyq = 0.5 * fs
        low_norm = low / nyq
        high_norm = high / nyq
        self.b, self.a = butter(order, [low_norm, high_norm], btype='band')
        self.latency_ms = 0.0

    def process(self, data: Dict[str, float], context: Any) -> tuple[Dict[str, float], Dict[str, Any]]:
        # Convert dict values to array
        """
        Process a dict of channel data by applying the band-pass filter.

        Parameters
        ----------
        data : dict[str, float]
            Channel data to filter
        context : Any
            Context information, not used

        Returns
        -------
        tuple[dict[str, float], dict[str, Any]]
            The filtered data and metrics (dict containing filter order)
        """
        channels = list(data.keys())
        arr = np.array([data[ch] for ch in channels])
        # Apply filter
        filtered = lfilter(self.b, self.a, arr)
        # Map back to dict
        result = {ch: float(filtered[i]) for i, ch in enumerate(channels)}
        metrics = {"filter_order": len(self.b)}
        return result, metrics
