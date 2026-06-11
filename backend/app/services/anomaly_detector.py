"""
NTES Anomaly Detection Service — IsolationForest and LSTM Autoencoder sequence model.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn


class NTESAnomalyDetector:
    """
    Detects anomalies in singular NTES telemetry reports (e.g. speed, delay spikes).
    Uses IsolationForest.
    """
    def __init__(self, contamination: float = 0.01):
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self._is_fitted = False
        
    def fit(self, X_train: np.ndarray) -> None:
        """Fits scale and IsolationForest on normal historical telemetry data."""
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled)
        self._is_fitted = True
        
    def score(self, X: np.ndarray) -> np.ndarray:
        """Returns anomaly score per sample. Lower = more anomalous."""
        if not self._is_fitted:
            raise RuntimeError("Detector is not fitted yet.")
        X_scaled = self.scaler.transform(X)
        return self.model.score_samples(X_scaled)
        
    def is_anomalous(self, X: np.ndarray, threshold: float = -0.55) -> np.ndarray:
        """Predicts if samples are anomalous based on threshold."""
        return self.score(X) < threshold


class LSTMAutoencoder(nn.Module):
    """
    PyTorch LSTM Autoencoder to detect temporal telemetry sequence anomalies.
    Trained on historical sequences; high reconstruction error indicates anomaly.
    """
    def __init__(self, input_dim: int = 5, hidden_dim: int = 64, n_layers: int = 2):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        
        self.encoder = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
        )
        
        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
        )
        
        self.output_proj = nn.Linear(hidden_dim, input_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x.size()
        
        # 1. Encode sequence to last hidden state
        _, (hidden, cell) = self.encoder(x)
        
        # 2. Replicate context vector for each decoder step
        # Take the top layer hidden state
        context = hidden[-1].unsqueeze(1)  # [batch, 1, hidden_dim]
        decoder_input = context.repeat(1, seq_len, 1)  # [batch, seq_len, hidden_dim]
        
        # 3. Decode
        decoded, _ = self.decoder(decoder_input)
        
        # 4. Project back to input feature space
        reconstructed = self.output_proj(decoded)
        return reconstructed
        
    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Returns Mean Squared Error (MSE) reconstruction loss per sequence."""
        self.eval()
        with torch.no_grad():
            x_hat = self.forward(x)
            # MSE loss over time dimension and feature dimension, keeping batch
            error = torch.mean((x - x_hat) ** 2, dim=[1, 2])
        return error
