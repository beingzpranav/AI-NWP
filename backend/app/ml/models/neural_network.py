"""
Two-Head Neural Network for Weather Forecasting.

Architecture:
    Input
    ↓ Dense(256) → BatchNorm → GELU → Dropout(0.3)
    ↓ Dense(128) → BatchNorm → GELU → Dropout(0.2)
    ↓ Dense(64)  → GELU
    ↓ Dense(32)  → Shared representation
    ├── HEAD 1 (Forecast): Dense(16) → Dense(n_targets) [linear]
    └── HEAD 2 (Uncertainty): Dense(16) → Dense(n_targets) [softplus → ≥0]

HEAD 1 minimizes MSE (weather prediction).
HEAD 2 predicts log-variance (heteroscedastic uncertainty).
Combined loss: NLL (negative log-likelihood) of Gaussian.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from typing import List, Optional, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TwoHeadWeatherNet(nn.Module):
    """
    Two-head ANN:
    - HEAD 1: Forecast (predicted weather values)
    - HEAD 2: Log-variance (uncertainty, converted to std via exp(0.5*log_var))
    """

    def __init__(self, input_dim: int, n_targets: int = 5):
        super().__init__()
        self.n_targets = n_targets

        # Shared trunk
        self.trunk = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.GELU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.Dropout(0.2),

            nn.Linear(128, 64),
            nn.GELU(),

            nn.Linear(64, 32),
            nn.GELU(),
        )

        # HEAD 1 — Forecast
        self.forecast_head = nn.Sequential(
            nn.Linear(32, 16),
            nn.GELU(),
            nn.Linear(16, n_targets),
        )

        # HEAD 2 — Log-variance (uncertainty)
        self.uncertainty_head = nn.Sequential(
            nn.Linear(32, 16),
            nn.GELU(),
            nn.Linear(16, n_targets),
        )

        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        shared = self.trunk(x)
        predictions = self.forecast_head(shared)
        log_variance = self.uncertainty_head(shared)
        return predictions, log_variance

    def predict_with_uncertainty(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Returns (predictions, std_dev)."""
        self.eval()
        with torch.no_grad():
            predictions, log_var = self.forward(x)
            std_dev = torch.exp(0.5 * log_var)  # σ = exp(log_σ²/2)
        return predictions, std_dev


def heteroscedastic_nll_loss(
    predictions: torch.Tensor,
    log_variance: torch.Tensor,
    targets: torch.Tensor,
) -> torch.Tensor:
    """
    Negative log-likelihood of Gaussian with predicted variance.
    Loss = 0.5 * (log_var + (target - pred)² / exp(log_var))
    This trains BOTH the prediction accuracy AND the uncertainty estimate.
    """
    precision = torch.exp(-log_variance)
    loss = 0.5 * (log_variance + precision * (targets - predictions) ** 2)
    return loss.mean()


class WeatherNeuralNetwork:
    """
    Training + inference wrapper for TwoHeadWeatherNet.
    """

    def __init__(
        self,
        input_dim: int,
        n_targets: int = 5,
        learning_rate: float = 1e-3,
        batch_size: int = 256,
        epochs: int = 100,
        patience: int = 15,
        weight_decay: float = 1e-4,
    ):
        self.input_dim = input_dim
        self.n_targets = n_targets
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        self.weight_decay = weight_decay
        self.net: Optional[TwoHeadWeatherNet] = None
        self.training_history: List[dict] = []
        self.is_fitted = False
        self.target_names: List[str] = []
        self.y_mean: Optional[np.ndarray] = None
        self.y_std: Optional[np.ndarray] = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        target_names: List[str] = None,
    ) -> "WeatherNeuralNetwork":
        self.net = TwoHeadWeatherNet(self.input_dim, self.n_targets).to(DEVICE)
        self.target_names = target_names or [f"target_{i}" for i in range(self.n_targets)]

        # Target standardization for stable neural network training
        self.y_mean = np.mean(y_train, axis=0, keepdims=True)
        self.y_std = np.std(y_train, axis=0, keepdims=True) + 1e-6
        y_train_norm = (y_train - self.y_mean) / self.y_std
        y_val_norm = (y_val - self.y_mean) / self.y_std

        optimizer = optim.AdamW(
            self.net.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )
        # Use ReduceLROnPlateau without deprecated verbose kwarg
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=7,
        )

        X_tr = torch.tensor(X_train, dtype=torch.float32).to(DEVICE)
        y_tr = torch.tensor(y_train_norm, dtype=torch.float32).to(DEVICE)
        X_v = torch.tensor(X_val, dtype=torch.float32).to(DEVICE)
        y_v = torch.tensor(y_val_norm, dtype=torch.float32).to(DEVICE)

        train_dataset = TensorDataset(X_tr, y_tr)
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        logger.info("ann_training_start", input_dim=self.input_dim,
                    n_targets=self.n_targets, device=str(DEVICE))

        for epoch in range(self.epochs):
            self.net.train()
            train_losses = []

            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                preds, log_var = self.net(X_batch)
                loss = heteroscedastic_nll_loss(preds, log_var, y_batch)
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())

            # Validation
            self.net.eval()
            with torch.no_grad():
                val_preds, val_log_var = self.net(X_v)
                val_loss = heteroscedastic_nll_loss(val_preds, val_log_var, y_v).item()
                val_mae = float(torch.mean(torch.abs(val_preds - y_v)).item())

            scheduler.step(val_loss)
            current_lr = optimizer.param_groups[0]["lr"]

            epoch_record = {
                "epoch": epoch + 1,
                "train_loss": float(np.mean(train_losses)),
                "val_loss": val_loss,
                "val_mae": val_mae,
                "lr": current_lr,
            }
            self.training_history.append(epoch_record)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in self.net.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            if (epoch + 1) % 10 == 0:
                logger.info("ann_epoch", **epoch_record)

            if patience_counter >= self.patience:
                logger.info("ann_early_stop", epoch=epoch + 1, best_val_loss=best_val_loss)
                break

        # Restore best weights
        if best_state:
            self.net.load_state_dict(best_state)

        self.is_fitted = True
        logger.info("ann_training_done", best_val_loss=best_val_loss)
        return self

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns (predictions, uncertainties) — both shape (n_samples, n_targets).
        """
        if not self.is_fitted:
            raise RuntimeError("Network not fitted — call fit() first")

        X_tensor = torch.tensor(X, dtype=torch.float32).to(DEVICE)
        preds, std = self.net.predict_with_uncertainty(X_tensor)
        preds_np = preds.cpu().numpy()
        std_np = std.cpu().numpy()
        if self.y_mean is not None and self.y_std is not None:
            preds_np = preds_np * self.y_std + self.y_mean
            std_np = std_np * self.y_std
        return preds_np, std_np

    def confidence_score(self, std_devs) -> float:
        """
        Convert uncertainty (std) to [0, 1] confidence score.
        Uses calibrated mapping. Higher std → lower confidence.
        Accepts scalar, ndarray, or float.
        """
        std_arr = np.asarray(std_devs, dtype=np.float32).ravel()
        if std_arr.size == 0:
            return 1.0
        mean_std = float(np.nanmean(np.maximum(0.0, std_arr)))
        return float(np.clip(1.0 / (1.0 + mean_std), 0.0, 1.0))

    def confidence_scores_batch(self, std_devs: np.ndarray) -> np.ndarray:
        """Convert per-sample uncertainty std to array of [0, 1] confidence scores."""
        std_arr = np.asarray(std_devs, dtype=np.float32)
        if std_arr.ndim > 1:
            mean_std = np.nanmean(std_arr, axis=-1)
        else:
            mean_std = std_arr
        return np.clip(1.0 / (1.0 + np.maximum(0.0, mean_std)), 0.0, 1.0)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "state_dict": self.net.state_dict() if self.net else None,
            "input_dim": self.input_dim,
            "n_targets": self.n_targets,
            "target_names": self.target_names,
            "training_history": self.training_history,
            "is_fitted": self.is_fitted,
            "y_mean": self.y_mean,
            "y_std": self.y_std,
        }, path)
        logger.info("ann_saved", path=path)

    @classmethod
    def load(cls, path: str) -> "WeatherNeuralNetwork":
        # weights_only=True avoids the FutureWarning in PyTorch >= 2.0
        try:
            checkpoint = torch.load(path, map_location=DEVICE, weights_only=False)
        except TypeError:
            # Older PyTorch versions don't support weights_only keyword
            checkpoint = torch.load(path, map_location=DEVICE)

        obj = cls(
            input_dim=checkpoint["input_dim"],
            n_targets=checkpoint["n_targets"],
        )
        obj.net = TwoHeadWeatherNet(
            checkpoint["input_dim"], checkpoint["n_targets"]
        ).to(DEVICE)
        if checkpoint.get("state_dict"):
            obj.net.load_state_dict(checkpoint["state_dict"])
        obj.target_names = checkpoint.get("target_names", [])
        obj.training_history = checkpoint.get("training_history", [])
        obj.is_fitted = checkpoint.get("is_fitted", False)
        obj.y_mean = checkpoint.get("y_mean", None)
        obj.y_std = checkpoint.get("y_std", None)
        logger.info("ann_loaded", path=path)
        return obj
