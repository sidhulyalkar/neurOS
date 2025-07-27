# training/transformer_pipeline.py
"""
Training pipeline for Transformer BCI models
Integrates with existing neurOS middleware and data catalog
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import wandb
from typing import Dict, Any, Tuple, Optional
import logging
from pathlib import Path
import json
from datetime import datetime

from models.transformers.transformer_bci import EEGNetTransformer, TransformerConfig
from middleware.data_layer.neuralake_catalog import BCI_CATALOG

logger = logging.getLogger(__name__)

class BCIDataset(Dataset):
    """Dataset class for BCI data compatible with PyTorch"""
    
    def __init__(self, eeg_data: np.ndarray, labels: np.ndarray, 
                 transform: Optional[callable] = None):
        """
        Args:
            eeg_data: EEG data of shape (n_trials, n_channels, n_timepoints)
            labels: Labels of shape (n_trials,)
            transform: Optional data transformation
        """
        self.eeg_data = eeg_data.astype(np.float32)
        self.labels = labels.astype(np.int64)
        self.transform = transform
        
    def __len__(self):
        return len(self.eeg_data)
    
    def __getitem__(self, idx):
        eeg = self.eeg_data[idx]
        label = self.labels[idx]
        
        if self.transform:
            eeg = self.transform(eeg)
            
        return torch.from_numpy(eeg), torch.tensor(label)

class EEGTransforms:
    """Data augmentation transforms for EEG data"""
    
    @staticmethod
    def normalize(eeg_data: np.ndarray) -> np.ndarray:
        """Z-score normalization per channel"""
        return (eeg_data - eeg_data.mean(axis=1, keepdims=True)) / \
               (eeg_data.std(axis=1, keepdims=True) + 1e-8)
    
    @staticmethod
    def add_noise(eeg_data: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        """Add Gaussian noise"""
        noise = np.random.normal(0, noise_level, eeg_data.shape)
        return eeg_data + noise
    
    @staticmethod
    def time_shift(eeg_data: np.ndarray, max_shift: int = 10) -> np.ndarray:
        """Random time shift augmentation"""
        shift = np.random.randint(-max_shift, max_shift + 1)
        if shift > 0:
            return np.pad(eeg_data[:, :-shift], ((0, 0), (shift, 0)), mode='edge')
        elif shift < 0:
            return np.pad(eeg_data[:, -shift:], ((0, 0), (0, -shift)), mode='edge')
        return eeg_data

class TransformerBCITrainer:
    """Training pipeline for transformer BCI models"""
    
    def __init__(self, config: TransformerConfig, use_wandb: bool = True):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_wandb = use_wandb
        
        # Initialize model
        self.model = EEGNetTransformer(config).to(self.device)
        
        # Loss and optimizer
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.AdamW(
            self.model.parameters(), 
            lr=config.learning_rate,
            weight_decay=0.01
        )
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=config.epochs
        )
        
        # Metrics tracking
        self.train_losses = []
        self.val_losses = []
        self.val_accuracies = []
        self.best_accuracy = 0.0
        
        # Initialize wandb if requested
        if self.use_wandb:
            wandb.init(
                project="neuros-transformer-bci",
                config=config.__dict__,
                name=f"transformer-bci-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
    
    def load_data_from_catalog(self) -> Tuple[np.ndarray, np.ndarray]:
        """Load data from neurOS data catalog"""
        logger.info("Loading data from neurOS catalog...")
        
        try:
            # Get cleaned EEG data from catalog
            cleaned_df = BCI_CATALOG.get_table("cleaned_eeg").collect()
            
            # Convert to numpy arrays
            # Assuming data format: columns are [trial_id, channel_0, channel_1, ..., channel_n, label]
            trial_ids = cleaned_df['trial_id'].unique().to_numpy()
            n_trials = len(trial_ids)
            n_channels = len([col for col in cleaned_df.columns if col.startswith('channel_')])
            n_timepoints = len(cleaned_df.filter(pl.col('trial_id') == trial_ids[0]))
            
            # Initialize arrays
            eeg_data = np.zeros((n_trials, n_channels, n_timepoints))
            labels = np.zeros(n_trials)
            
            # Fill arrays
            for i, trial_id in enumerate(trial_ids):
                trial_data = cleaned_df.filter(pl.col('trial_id') == trial_id)
                
                # Extract EEG channels
                for ch in range(n_channels):
                    eeg_data[i, ch, :] = trial_data[f'channel_{ch}'].to_numpy()
                
                # Extract label
                labels[i] = trial_data['label'][0]
            
            logger.info(f"Loaded {n_trials} trials with {n_channels} channels and {n_timepoints} timepoints")
            return eeg_data, labels
            
        except Exception as e:
            logger.warning(f"Could not load from catalog: {e}")
            logger.info("Generating synthetic data for demonstration...")
            return self.generate_synthetic_data()
    
    def generate_synthetic_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic EEG data for demonstration"""
        n_trials = 500
        n_channels = self.config.n_channels
        n_timepoints = self.config.seq_length
        
        # Generate synthetic motor imagery data
        eeg_data = np.random.randn(n_trials, n_channels, n_timepoints)
        
        # Add realistic EEG characteristics
        for trial in range(n_trials):
            for ch in range(n_channels):
                # Add 1/f noise
                freqs = np.fft.fftfreq(n_timepoints, 1/self.config.sampling_rate)
                noise_spectrum = 1 / (1 + freqs[1:len(freqs)//2]**2)
                noise_signal = np.fft.irfft(noise_spectrum, n_timepoints)
                eeg_data[trial, ch, :] += noise_signal[:n_timepoints] * 0.5
                
                # Add alpha rhythm (8-12 Hz)
                t = np.arange(n_timepoints) / self.config.sampling_rate
                alpha_freq = np.random.uniform(8, 12)
                alpha_signal = np.sin(2 * np.pi * alpha_freq * t) * 0.3
                eeg_data[trial, ch, :] += alpha_signal
        
        # Generate labels (motor imagery: left vs right)
        labels = np.random.randint(0, self.config.n_classes, n_trials)
        
        # Add class-specific patterns
        for trial in range(n_trials):
            if labels[trial] == 0:  # Left motor imagery
                # Enhance activity in right hemisphere (channels 32-63)
                eeg_data[trial, 32:64, :] *= 1.2
            else:  # Right motor imagery
                # Enhance activity in left hemisphere (channels 0-31)
                eeg_data[trial, 0:32, :] *= 1.2
        
        logger.info(f"Generated {n_trials} synthetic trials")
        return eeg_data, labels
    
    def prepare_datasets(self, eeg_data: np.ndarray, labels: np.ndarray, 
                        test_size: float = 0.2, val_size: float = 0.1) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """Prepare train, validation, and test datasets"""
        
        # Split data
        X_temp, X_test, y_temp, y_test = train_test_split(
            eeg_data, labels, test_size=test_size, stratify=labels, random_state=42
        )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size/(1-test_size), stratify=y_temp, random_state=42
        )
        
        # Create datasets with transforms
        train_transform = lambda x: EEGTransforms.add_noise(EEGTransforms.normalize(x), 0.01)
        val_transform = EEGTransforms.normalize
        
        train_dataset = BCIDataset(X_train, y_train, transform=train_transform)
        val_dataset = BCIDataset(X_val, y_val, transform=val_transform)
        test_dataset = BCIDataset(X_test, y_test, transform=val_transform)
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset, batch_size=self.config.batch_size, 
            shuffle=True, num_workers=4, pin_memory=True
        )
        val_loader = DataLoader(
            val_dataset, batch_size=self.config.batch_size, 
            shuffle=False, num_workers=4, pin_memory=True
        )
        test_loader = DataLoader(
            test_dataset, batch_size=self.config.batch_size, 
            shuffle=False, num_workers=4, pin_memory=True
        )
        
        logger.info(f"Dataset splits - Train: {len(train_dataset)}, Val: {len(val_dataset)}, Test: {len(test_dataset)}")
        return train_loader, val_loader, test_loader
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.criterion(output, target)
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)
            
            if batch_idx % 10 == 0:
                logger.debug(f'Batch {batch_idx}/{len(train_loader)}, Loss: {loss.item():.6f}')
        
        avg_loss = total_loss / len(train_loader)
        accuracy = 100. * correct / total
        return avg_loss, accuracy
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """Validate the model"""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = self.criterion(output, target)
                
                total_loss += loss.item()
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = 100. * correct / total
        return avg_loss, accuracy
    
    def train(self, save_dir: str = "./models") -> Dict[str, Any]:
        """Full training pipeline"""
        logger.info("Starting transformer BCI training...")
        
        # Load data
        eeg_data, labels = self.load_data_from_catalog()
        train_loader, val_loader, test_loader = self.prepare_datasets(eeg_data, labels)
        
        # Create save directory
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Training loop
        for epoch in range(self.config.epochs):
            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)
            
            self.scheduler.step()
            
            # Track metrics
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            self.val_accuracies.append(val_acc)
            
            # Log to wandb
            if self.use_wandb:
                wandb.log({
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "train_accuracy": train_acc,
                    "val_loss": val_loss,
                    "val_accuracy": val_acc,
                    "learning_rate": self.scheduler.get_last_lr()[0]
                })
            
            # Save best model
            if val_acc > self.best_accuracy:
                self.best_accuracy = val_acc
                model_path = save_path / "best_model.pth"
                torch.save(self.model.state_dict(), model_path)
                
                # Save config too
                config_path = save_path / "config.json"
                with open(config_path, 'w') as f:
                    json.dump(self.config.__dict__, f, indent=2)
            
            logger.info(f'Epoch {epoch+1}/{self.config.epochs}: '
                       f'Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, '
                       f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
        
        # Final test evaluation
        test_loss, test_acc = self.validate(test_loader)
        logger.info(f'Final Test Accuracy: {test_acc:.2f}%')
        
        # Save final model
        final_model_path = save_path / "final_model.pth"
        torch.save(self.model.state_dict(), final_model_path)
        
        if self.use_wandb:
            wandb.log({"test_accuracy": test_acc})
            wandb.finish()
        
        return {
            "best_val_accuracy": self.best_accuracy,
            "test_accuracy": test_acc,
            "model_path": str(final_model_path),
            "config_path": str(config_path)
        }

# Integration with neurOS dashboard
def create_training_dashboard():
    """Create Streamlit dashboard for training monitoring"""
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    
    st.title("🧠 Transformer BCI Training Dashboard")
    
    # Configuration sidebar
    st.sidebar.title("Training Configuration")
    
    # Model parameters
    n_channels = st.sidebar.slider("Number of Channels", 32, 128, 64)
    seq_length = st.sidebar.slider("Sequence Length", 500, 2000, 1000)
    d_model = st.sidebar.selectbox("Model Dimension", [128, 256, 512], index=1)
    n_heads = st.sidebar.selectbox("Attention Heads", [4, 8, 16], index=1)
    n_layers = st.sidebar.slider("Transformer Layers", 2, 8, 4)
    
    # Training parameters
    batch_size = st.sidebar.selectbox("Batch Size", [16, 32, 64], index=1)
    learning_rate = st.sidebar.selectbox("Learning Rate", [0.0001, 0.001, 0.01], index=1)
    epochs = st.sidebar.slider("Epochs", 10, 200, 50)
    
    # Task selection
    task_type = st.sidebar.selectbox("Task Type", ["motor_imagery", "p300", "ssvep"])
    n_classes = st.sidebar.slider("Number of Classes", 2, 10, 2)
    
    config = TransformerConfig(
        n_channels=n_channels,
        seq_length=seq_length,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        batch_size=batch_size,
        learning_rate=learning_rate,
        epochs=epochs,
        task_type=task_type,
        n_classes=n_classes
    )
    
    # Display current configuration
    st.sidebar.json(config.__dict__)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Training Progress")
        
        if st.button("Start Training", type="primary"):
            with st.spinner("Training transformer model..."):
                trainer = TransformerBCITrainer(config, use_wandb=False)
                
                # Create placeholder for real-time updates
                loss_chart = st.empty()
                acc_chart = st.empty()
                metrics_table = st.empty()
                
                try:
                    results = trainer.train()
                    
                    # Display results
                    st.success(f"Training completed! Best validation accuracy: {results['best_val_accuracy']:.2f}%")
                    st.success(f"Test accuracy: {results['test_accuracy']:.2f}%")
                    
                    # Plot training curves
                    fig_loss = go.Figure()
                    fig_loss.add_trace(go.Scatter(
                        y=trainer.train_losses,
                        name="Training Loss",
                        line=dict(color='blue')
                    ))
                    fig_loss.add_trace(go.Scatter(
                        y=trainer.val_losses,
                        name="Validation Loss",
                        line=dict(color='red')
                    ))
                    fig_loss.update_layout(title="Training and Validation Loss", xaxis_title="Epoch", yaxis_title="Loss")
                    st.plotly_chart(fig_loss, use_container_width=True)
                    
                    fig_acc = go.Figure()
                    fig_acc.add_trace(go.Scatter(
                        y=trainer.val_accuracies,
                        name="Validation Accuracy",
                        line=dict(color='green')
                    ))
                    fig_acc.update_layout(title="Validation Accuracy", xaxis_title="Epoch", yaxis_title="Accuracy (%)")
                    st.plotly_chart(fig_acc, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Training failed: {e}")
    
    with col2:
        st.subheader("🎯 Model Architecture")
        
        # Model summary
        st.write("**EEGNet-Transformer Hybrid**")
        st.write(f"• Input: {n_channels} channels × {seq_length} samples")
        st.write(f"• CNN Feature Extraction")
        st.write(f"• Transformer: {n_layers} layers, {n_heads} heads")
        st.write(f"• Hidden Dimension: {d_model}")
        st.write(f"• Output: {n_classes} classes")
        
        # Calculate model parameters
        model = EEGNetTransformer(config)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        st.write(f"**Parameters:**")
        st.write(f"• Total: {total_params:,}")
        st.write(f"• Trainable: {trainable_params:,}")
        
        # Memory estimation
        model_size_mb = total_params * 4 / (1024 * 1024)  # Assuming float32
        st.write(f"• Model Size: {model_size_mb:.1f} MB")
        
        st.subheader("📈 Expected Performance")
        st.write("**Motor Imagery BCI:**")
        st.write("• Baseline: ~70-75%")
        st.write("• Target: >85%")
        st.write("• SOTA: ~90%")
        
        st.write("**Latency Targets:**")
        st.write("• Training: <500ms/batch")
        st.write("• Inference: <50ms")
        st.write("• Real-time: <100ms")

# CLI integration
def run_training_from_cli(config_path: Optional[str] = None, 
                         output_dir: str = "./models",
                         use_wandb: bool = True) -> Dict[str, Any]:
    """Run training from command line"""
    
    # Load config
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        config = TransformerConfig(**config_dict)
    else:
        # Use default config
        config = TransformerConfig()
    
    # Initialize trainer
    trainer = TransformerBCITrainer(config, use_wandb=use_wandb)
    
    # Run training
    results = trainer.train(save_dir=output_dir)
    
    logger.info("Training completed successfully!")
    logger.info(f"Best validation accuracy: {results['best_val_accuracy']:.2f}%")
    logger.info(f"Test accuracy: {results['test_accuracy']:.2f}%")
    logger.info(f"Model saved to: {results['model_path']}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Transformer BCI Model")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--output", type=str, default="./models", help="Output directory")
    parser.add_argument("--no-wandb", action="store_true", help="Disable wandb logging")
    
    args = parser.parse_args()
    
    run_training_from_cli(
        config_path=args.config,
        output_dir=args.output,
        use_wandb=not args.no_wandb
    )