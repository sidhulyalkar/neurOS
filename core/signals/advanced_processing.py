# neuros/core/signals/advanced_processing.py
"""
Advanced Signal Processing for BCI with Time-Frequency Features
Optimized for motor imagery, P300, and SSVEP classification
"""

import numpy as np
import scipy.signal as signal
from scipy import linalg
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Dict, Any, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

class BCITask(Enum):
    MOTOR_IMAGERY = "motor_imagery"
    P300 = "p300"
    SSVEP = "ssvep"
    GENERIC = "generic"

@dataclass
class SignalConfig:
    """Configuration for signal processing"""
    sample_rate: int = 250
    channels: int = 64
    task_type: BCITask = BCITask.MOTOR_IMAGERY
    freq_bands: Dict[str, Tuple[float, float]] = None
    
    def __post_init__(self):
        if self.freq_bands is None:
            self.freq_bands = {
                'delta': (1, 4),
                'theta': (4, 8),
                'alpha': (8, 13),
                'beta': (13, 30),
                'gamma': (30, 100)
            }

class SpatialFilters:
    """Advanced spatial filtering methods for BCI"""
    
    @staticmethod
    def csp(X1: np.ndarray, X2: np.ndarray, n_components: int = 6) -> Tuple[np.ndarray, np.ndarray]:
        """
        Common Spatial Patterns (CSP) for motor imagery
        
        Args:
            X1: EEG data for class 1 (trials x channels x time)
            X2: EEG data for class 2 (trials x channels x time)
            n_components: Number of CSP components to return
            
        Returns:
            Spatial filters and eigenvalues
        """
        # Compute covariance matrices
        def cov_matrix(X):
            n_trials, n_channels, n_times = X.shape
            cov = np.zeros((n_channels, n_channels))
            for trial in range(n_trials):
                trial_data = X[trial]
                cov += np.cov(trial_data)
            return cov / n_trials
        
        C1 = cov_matrix(X1)
        C2 = cov_matrix(X2)
        
        # Solve generalized eigenvalue problem
        eigenvals, eigenvecs = linalg.eigh(C1, C1 + C2)
        
        # Sort by eigenvalues
        order = np.argsort(eigenvals)[::-1]
        eigenvals = eigenvals[order]
        eigenvecs = eigenvecs[:, order]
        
        # Select components (most discriminative)
        n_comp_half = n_components // 2
        selected_indices = np.concatenate([
            np.arange(n_comp_half),  # Largest eigenvalues
            np.arange(-n_comp_half, 0)  # Smallest eigenvalues
        ])
        
        spatial_filters = eigenvecs[:, selected_indices]
        selected_eigenvals = eigenvals[selected_indices]
        
        return spatial_filters, selected_eigenvals
    
    @staticmethod
    def xdawn(X: np.ndarray, y: np.ndarray, n_components: int = 8) -> np.ndarray:
        """
        xDAWN spatial filters for P300 enhancement
        
        Args:
            X: EEG data (trials x channels x time)
            y: Binary labels (1 for target, 0 for non-target)
            n_components: Number of components
            
        Returns:
            Spatial filters
        """
        n_trials, n_channels, n_times = X.shape
        
        # Create Toeplitz matrix for each trial
        def create_toeplitz(trial_data):
            return signal.hilbert(trial_data.T)  # Simplified version
        
        # Compute covariance matrices
        target_trials = X[y == 1]
        nontarget_trials = X[y == 0]
        
        # Average ERPs
        target_erp = np.mean(target_trials, axis=0)
        nontarget_erp = np.mean(nontarget_trials, axis=0)
        
        # Compute signal and noise covariance
        S = np.cov(target_erp)  # Signal covariance
        N = np.cov(nontarget_erp)  # Noise covariance
        
        # Generalized eigenvalue decomposition
        eigenvals, eigenvecs = linalg.eigh(S, S + N)
        
        # Sort and select components
        order = np.argsort(eigenvals)[::-1]
        spatial_filters = eigenvecs[:, order[:n_components]]
        
        return spatial_filters
    
    @staticmethod
    def cca_ssvep(X: np.ndarray, freqs: List[float], sample_rate: int, 
                  n_harmonics: int = 3) -> Tuple[np.ndarray, List[float]]:
        """
        Canonical Correlation Analysis for SSVEP
        
        Args:
            X: EEG data (trials x channels x time)
            freqs: Target frequencies
            sample_rate: Sampling rate
            n_harmonics: Number of harmonics to include
            
        Returns:
            CCA coefficients and correlation values
        """
        n_trials, n_channels, n_times = X.shape
        time_points = np.arange(n_times) / sample_rate
        
        correlations = []
        coefficients = []
        
        for freq in freqs:
            # Create reference signals
            references = []
            for h in range(1, n_harmonics + 1):
                references.append(np.sin(2 * np.pi * h * freq * time_points))
                references.append(np.cos(2 * np.pi * h * freq * time_points))
            
            Y = np.array(references)
            
            # CCA for each trial
            trial_corrs = []
            trial_coeffs = []
            
            for trial in range(n_trials):
                trial_data = X[trial]
                
                # Center the data
                X_centered = trial_data - np.mean(trial_data, axis=1, keepdims=True)
                Y_centered = Y - np.mean(Y, axis=1, keepdims=True)
                
                # Compute cross-correlation
                C_xx = np.cov(X_centered)
                C_yy = np.cov(Y_centered)
                C_xy = np.cov(X_centered, Y_centered)[:n_channels, n_channels:]
                
                # Solve CCA
                try:
                    # Regularized version for numerical stability
                    reg = 1e-6
                    C_xx_reg = C_xx + reg * np.eye(C_xx.shape[0])
                    C_yy_reg = C_yy + reg * np.eye(C_yy.shape[0])
                    
                    A = linalg.solve(C_xx_reg, C_xy)
                    B = linalg.solve(C_yy_reg, C_xy.T)
                    
                    # Canonical correlation
                    corr_matrix = A @ B
                    eigenvals, eigenvecs = linalg.eigh(corr_matrix)
                    max_corr = np.sqrt(np.max(eigenvals))
                    
                    trial_corrs.append(max_corr)
                    trial_coeffs.append(eigenvecs[:, -1])  # Best component
                    
                except:
                    trial_corrs.append(0.0)
                    trial_coeffs.append(np.zeros(n_channels))
            
            correlations.append(np.mean(trial_corrs))
            coefficients.append(np.mean(trial_coeffs, axis=0))
        
        return np.array(coefficients), correlations

class TimeFrequencyFeatures:
    """Advanced time-frequency feature extraction"""
    
    @staticmethod
    def wavelet_transform(data: np.ndarray, sample_rate: int, 
                         freqs: np.ndarray = None) -> np.ndarray:
        """
        Continuous Wavelet Transform using Morlet wavelets
        
        Args:
            data: EEG data (channels x time)
            sample_rate: Sampling rate
            freqs: Frequencies to analyze
            
        Returns:
            Complex wavelet coefficients (channels x frequencies x time)
        """
        if freqs is None:
            freqs = np.logspace(np.log10(1), np.log10(50), 30)
        
        n_channels, n_times = data.shape
        n_freqs = len(freqs)
        
        # Wavelet parameters
        sigma = 7.0  # Wavelet width parameter
        
        coefficients = np.zeros((n_channels, n_freqs, n_times), dtype=complex)
        
        for ch in range(n_channels):
            for f_idx, freq in enumerate(freqs):
                # Create Morlet wavelet
                wavelet_length = int(sample_rate * sigma / freq)
                if wavelet_length % 2 == 0:
                    wavelet_length += 1
                
                t_wavelet = np.arange(-wavelet_length//2, wavelet_length//2 + 1) / sample_rate
                wavelet = (np.pi**(-0.25)) * np.exp(1j * 2 * np.pi * freq * t_wavelet) * \
                         np.exp(-t_wavelet**2 / (2 * (sigma / (2 * np.pi * freq))**2))
                
                # Convolution
                coefficients[ch, f_idx, :] = np.convolve(data[ch], wavelet, mode='same')
        
        return coefficients
    
    @staticmethod
    def spectral_power_features(data: np.ndarray, sample_rate: int, 
                               freq_bands: Dict[str, Tuple[float, float]]) -> Dict[str, np.ndarray]:
        """
        Extract spectral power features in specific frequency bands
        
        Args:
            data: EEG data (channels x time)
            sample_rate: Sampling rate
            freq_bands: Dictionary of frequency bands
            
        Returns:
            Power features for each band
        """
        n_channels, n_times = data.shape
        features = {}
        
        # Compute power spectral density
        freqs, psd = signal.welch(data, fs=sample_rate, nperseg=min(256, n_times//4))
        
        for band_name, (low_freq, high_freq) in freq_bands.items():
            # Find frequency indices
            freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
            
            if np.any(freq_mask):
                # Average power in the band
                band_power = np.mean(psd[:, freq_mask], axis=1)
                features[band_name] = band_power
            else:
                features[band_name] = np.zeros(n_channels)
        
        return features
    
    @staticmethod
    def time_frequency_decomposition(data: np.ndarray, sample_rate: int) -> Dict[str, np.ndarray]:
        """
        Complete time-frequency decomposition with multiple methods
        
        Args:
            data: EEG data (channels x time)
            sample_rate: Sampling rate
            
        Returns:
            Dictionary of time-frequency features
        """
        features = {}
        
        # 1. Short-Time Fourier Transform
        f_stft, t_stft, Zxx = signal.stft(data, fs=sample_rate, nperseg=128)
        features['stft_magnitude'] = np.abs(Zxx)
        features['stft_phase'] = np.angle(Zxx)
        
        # 2. Wavelet Transform
        freqs = np.logspace(np.log10(1), np.log10(50), 20)
        wavelet_coeffs = TimeFrequencyFeatures.wavelet_transform(data, sample_rate, freqs)
        features['wavelet_power'] = np.abs(wavelet_coeffs)**2
        features['wavelet_phase'] = np.angle(wavelet_coeffs)
        
        # 3. Hilbert Transform for instantaneous features
        analytic_signal = signal.hilbert(data, axis=1)
        features['instantaneous_amplitude'] = np.abs(analytic_signal)
        features['instantaneous_phase'] = np.angle(analytic_signal)
        features['instantaneous_frequency'] = np.diff(np.unwrap(np.angle(analytic_signal), axis=1), axis=1) * sample_rate / (2 * np.pi)
        
        return features

class AdvancedFeatureExtractor(BaseEstimator, TransformerMixin):
    """Complete feature extraction pipeline for BCI"""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        self.spatial_filters_ = None
        self.feature_names_ = []
        self.logger = logging.getLogger("neurOS.features")
    
    def fit(self, X: np.ndarray, y: np.ndarray = None) -> 'AdvancedFeatureExtractor':
        """
        Fit the feature extractor
        
        Args:
            X: EEG data (trials x channels x time)
            y: Labels for supervised spatial filtering
        """
        self.logger.info(f"Fitting feature extractor for {self.config.task_type.value}")
        
        # Task-specific spatial filtering
        if self.config.task_type == BCITask.MOTOR_IMAGERY and y is not None:
            # CSP for motor imagery
            unique_labels = np.unique(y)
            if len(unique_labels) == 2:
                X1 = X[y == unique_labels[0]]
                X2 = X[y == unique_labels[1]]
                self.spatial_filters_, _ = SpatialFilters.csp(X1, X2, n_components=8)
                self.logger.info("CSP spatial filters computed")
        
        elif self.config.task_type == BCITask.P300 and y is not None:
            # xDAWN for P300
            self.spatial_filters_ = SpatialFilters.xdawn(X, y, n_components=8)
            self.logger.info("xDAWN spatial filters computed")
        
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Extract features from EEG data
        
        Args:
            X: EEG data (trials x channels x time)
            
        Returns:
            Feature matrix (trials x features)
        """
        n_trials, n_channels, n_times = X.shape
        all_features = []
        
        for trial_idx in range(n_trials):
            trial_data = X[trial_idx]
            
            # Apply spatial filtering if available
            if self.spatial_filters_ is not None:
                trial_data = self.spatial_filters_.T @ trial_data
            
            trial_features = self._extract_trial_features(trial_data)
            all_features.append(trial_features)
        
        feature_matrix = np.array(all_features)
        self.logger.info(f"Extracted features shape: {feature_matrix.shape}")
        
        return feature_matrix
    
    def _extract_trial_features(self, data: np.ndarray) -> np.ndarray:
        """Extract features from a single trial"""
        features = []
        feature_names = []
        
        n_channels, n_times = data.shape
        
        # 1. Spectral power features
        power_features = TimeFrequencyFeatures.spectral_power_features(
            data, self.config.sample_rate, self.config.freq_bands
        )
        
        for band_name, band_power in power_features.items():
            features.extend(band_power)
            feature_names.extend([f"{band_name}_power_ch{i}" for i in range(len(band_power))])
        
        # 2. Time-frequency features
        tf_features = TimeFrequencyFeatures.time_frequency_decomposition(
            data, self.config.sample_rate
        )
        
        # Average wavelet power across time for each frequency and channel
        if 'wavelet_power' in tf_features:
            wavelet_power_avg = np.mean(tf_features['wavelet_power'], axis=2)  # Average over time
            for ch in range(wavelet_power_avg.shape[0]):
                for freq_idx in range(wavelet_power_avg.shape[1]):
                    features.append(wavelet_power_avg[ch, freq_idx])
                    feature_names.append(f"wavelet_power_ch{ch}_freq{freq_idx}")
        
        # 3. Statistical features
        for ch in range(n_channels):
            ch_data = data[ch]
            
            # Time domain statistics
            features.extend([
                np.mean(ch_data),
                np.std(ch_data),
                np.var(ch_data),
                np.max(ch_data) - np.min(ch_data),  # Peak-to-peak
                np.percentile(ch_data, 75) - np.percentile(ch_data, 25),  # IQR
            ])
            
            feature_names.extend([
                f"mean_ch{ch}", f"std_ch{ch}", f"var_ch{ch}", 
                f"ptp_ch{ch}", f"iqr_ch{ch}"
            ])
        
        # 4. Connectivity features (simplified)
        correlation_matrix = np.corrcoef(data)
        upper_tri_indices = np.triu_indices(n_channels, k=1)
        correlations = correlation_matrix[upper_tri_indices]
        
        features.extend(correlations)
        feature_names.extend([f"corr_ch{i}_ch{j}" for i, j in zip(*upper_tri_indices)])
        
        # Store feature names (only once)
        if not self.feature_names_:
            self.feature_names_ = feature_names
        
        return np.array(features)
    
    def get_feature_names(self) -> List[str]:
        """Get names of extracted features"""
        return self.feature_names_

# Task-specific feature extractors
class MotorImageryFeatures(AdvancedFeatureExtractor):
    """Specialized feature extraction for motor imagery"""
    
    def __init__(self, sample_rate: int = 250, channels: int = 64):
        config = SignalConfig(
            sample_rate=sample_rate,
            channels=channels,
            task_type=BCITask.MOTOR_IMAGERY,
            freq_bands={
                'mu': (8, 12),      # Mu rhythm
                'beta': (13, 30),   # Beta rhythm
                'low_gamma': (30, 50)  # Low gamma
            }
        )
        super().__init__(config)

class P300Features(AdvancedFeatureExtractor):
    """Specialized feature extraction for P300"""
    
    def __init__(self, sample_rate: int = 250, channels: int = 64):
        config = SignalConfig(
            sample_rate=sample_rate,
            channels=channels,
            task_type=BCITask.P300,
            freq_bands={
                'delta': (1, 4),
                'theta': (4, 8),
                'alpha': (8, 13),
                'beta': (13, 30)
            }
        )
        super().__init__(config)

class SSVEPFeatures(AdvancedFeatureExtractor):
    """Specialized feature extraction for SSVEP"""
    
    def __init__(self, sample_rate: int = 250, channels: int = 64, target_freqs: List[float] = None):
        if target_freqs is None:
            target_freqs = [6.0, 7.5, 8.57, 10.0, 12.0]  # Common SSVEP frequencies
        
        config = SignalConfig(
            sample_rate=sample_rate,
            channels=channels,
            task_type=BCITask.SSVEP,
            freq_bands={f'ssvep_{f}hz': (f-0.5, f+0.5) for f in target_freqs}
        )
        super().__init__(config)
        self.target_freqs = target_freqs

# Example usage and testing
if __name__ == "__main__":
    # Test feature extraction
    sample_rate = 250
    n_channels = 32
    n_times = 500  # 2 seconds
    n_trials = 100
    
    # Generate synthetic data
    np.random.seed(42)
    X = np.random.randn(n_trials, n_channels, n_times)
    y = np.random.randint(0, 2, n_trials)  # Binary labels
    
    print("Testing Motor Imagery Feature Extraction:")
    mi_extractor = MotorImageryFeatures(sample_rate, n_channels)
    mi_extractor.fit(X, y)
    mi_features = mi_extractor.transform(X[:10])  # Test on 10 trials
    print(f"MI Features shape: {mi_features.shape}")
    print(f"Number of features: {len(mi_extractor.get_feature_names())}")
    
    print("\nTesting P300 Feature Extraction:")
    p300_extractor = P300Features(sample_rate, n_channels)
    p300_extractor.fit(X, y)
    p300_features = p300_extractor.transform(X[:10])
    print(f"P300 Features shape: {p300_features.shape}")
    print(f"Number of features: {len(p300_extractor.get_feature_names())}")
    
    print("\nTesting SSVEP Feature Extraction:")
    ssvep_extractor = SSVEPFeatures(sample_rate, n_channels)
    ssvep_extractor.fit(X, y)
    ssvep_features = ssvep_extractor.transform(X[:10])
    print(f"SSVEP Features shape: {ssvep_features.shape}")
    print(f"Number of features: {len(ssvep_extractor.get_feature_names())}")
    
    # Test individual components
    print("\nTesting CSP:")
    X1 = X[y == 0][:20]  # Class 1 data
    X2 = X[y == 1][:20]  # Class 2 data
    spatial_filters, eigenvals = SpatialFilters.csp(X1, X2, n_components=6)
    print(f"CSP filters shape: {spatial_filters.shape}")
    print(f"Eigenvalues: {eigenvals}")
    
    print("\nTesting Time-Frequency Features:")
    single_trial = X[0]  # Single trial
    tf_features = TimeFrequencyFeatures.time_frequency_decomposition(single_trial, sample_rate)
    for name, feature in tf_features.items():
        print(f"{name} shape: {feature.shape}")
    
    print("\n✅ All signal processing tests completed successfully!")