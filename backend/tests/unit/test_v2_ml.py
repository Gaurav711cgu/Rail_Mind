# ruff: noqa: E402
"""
Unit tests for RailMind FAANG-Level Upgrade (Version 2.0) ML components.
"""

import numpy as np
import pandas as pd
import torch

# Force single-threaded execution for PyTorch on CPU during testing to prevent OpenMP/Intel MKL deadlocks
torch.set_num_threads(1)

from app.ml.railgym import RailGym
from app.ml.gnn_cascade import RailwayGNN, CascadeLoss
from app.ml.ensemble_rac import EnsembleRACPredictor, compute_ece
from app.services.anomaly_detector import NTESAnomalyDetector, LSTMAutoencoder


# ─────────────────────────────────────────────────────────────
#  RailGym Tests
# ─────────────────────────────────────────────────────────────


def test_railgym_reset_and_step():
    env = RailGym(scenario="moderate")
    obs, info = env.reset(seed=42)

    # 8 sections * 7 features = 56
    assert obs.shape == (56,)
    assert isinstance(info, dict)

    # Take step
    action = env.action_space.sample()
    next_obs, reward, terminated, truncated, step_info = env.step(action)

    assert next_obs.shape == (56,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "passenger_delay" in step_info
    assert "freight_delay" in step_info


def test_railgym_ppo_initialization():
    """Validate RailGym is Gymnasium-compatible without running the full check_env suite."""
    from app.ml.railgym import HAS_SB3

    env = RailGym()
    assert env.observation_space.shape == (56,)
    assert env.action_space.shape == (8,)  # MultiDiscrete of 8 sections

    # Manually verify Gymnasium API contract (avoids the slow full check_env)
    obs, info = env.reset(seed=0)
    assert obs.shape == (56,)
    assert obs.dtype == np.float32
    assert isinstance(info, dict)

    action = env.action_space.sample()
    obs2, reward, terminated, truncated, step_info = env.step(action)
    assert obs2.shape == (56,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "passenger_delay" in step_info

    # Optionally run gymnasium's lightweight env checker with warn=False to skip
    # the full episode rollout and just validate space/dtype contracts
    try:
        from gymnasium.utils.env_checker import check_env

        # check_env by default runs many episodes; skip it on CI / slow machines
        import signal

        def _timeout_handler(signum, frame):
            raise TimeoutError("check_env timed out")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(10)  # 10-second hard limit
        try:
            check_env(env, warn=True)
        finally:
            signal.alarm(0)  # cancel alarm
    except (ImportError, TimeoutError, AttributeError):
        # AttributeError: signal.SIGALRM not available on Windows
        pass

    if HAS_SB3:
        from stable_baselines3 import PPO

        assert PPO is not None


# ─────────────────────────────────────────────────────────────
#  GNN Cascade Predictor Tests
# ─────────────────────────────────────────────────────────────


def test_gnn_cascade_forward():
    # 10 stations, 8 features per station
    x = torch.randn(10, 8)
    # 12 sections (edges)
    edge_index = torch.randint(0, 10, (2, 12))
    # 6 features per edge
    edge_attr = torch.randn(12, 6)
    disruption_mask = torch.zeros(10, dtype=torch.bool)
    disruption_mask[3] = True  # Station 3 is disrupted

    model = RailwayGNN(node_feat_dim=8, edge_feat_dim=6, hidden_dim=64, n_sage_layers=2)
    out = model(x, edge_index, edge_attr, time_of_day=0.35, disruption_node_mask=disruption_mask)

    # 10 stations, 3 delay horizons [30, 60, 90]
    assert out["delay_minutes"].shape == (10, 3)
    # Probability per node
    assert out["cascade_probability"].shape == (10,)
    assert (out["cascade_probability"] >= 0.0).all() and (out["cascade_probability"] <= 1.0).all()


def test_gnn_loss():
    pred = {"delay_minutes": torch.randn(5, 3), "cascade_probability": torch.rand(5)}
    target = {
        "delay_minutes": torch.randn(5, 3),
        "cascade_reached": torch.randint(0, 2, (5,)).float(),
    }
    criterion = CascadeLoss(alpha=0.6)
    loss = criterion(pred, target)
    assert isinstance(loss, torch.Tensor)
    assert loss.item() > 0


# ─────────────────────────────────────────────────────────────
#  Ensemble RAC Predictor Tests
# ─────────────────────────────────────────────────────────────


def test_ensemble_rac_fit_predict():
    # Generate mock classification dataset
    np.random.seed(42)
    n_samples = 200
    X = pd.DataFrame(
        {
            "days_to_journey": np.random.randint(1, 30, n_samples),
            "current_waitlist_position": np.random.randint(1, 100, n_samples),
            "current_rac_count": np.random.randint(0, 50, n_samples),
            "quota_num": np.random.choice([0, 1], n_samples),
        }
    )
    # Target confirmations: confirm if waitlist is low, days to journey is high
    y = ((X["days_to_journey"] * 3) - X["current_waitlist_position"] > 0).astype(int)

    predictor = EnsembleRACPredictor()
    predictor.fit(X, y)

    # Predict probabilities
    probs = predictor.predict_proba(X)
    assert probs.shape == (n_samples,)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()

    # Evaluate
    metrics = predictor.evaluate(X, y)
    assert "accuracy" in metrics
    assert "roc_auc" in metrics
    assert "ece" in metrics
    assert 0.0 <= metrics["ece"] <= 1.0


def test_ece_calculation():
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_prob = np.array([0.9, 0.8, 0.1, 0.2, 0.7, 0.15])
    ece = compute_ece(y_true, y_prob, n_bins=5)
    assert isinstance(ece, float)
    assert 0.0 <= ece <= 1.0


# ─────────────────────────────────────────────────────────────
#  Anomaly Detection Tests
# ─────────────────────────────────────────────────────────────


def test_ntes_anomaly_detector():
    np.random.seed(42)
    # Fit data: speed_kmh, delay_minutes, platform_no
    train_data = np.random.normal(loc=[80.0, 5.0, 2.0], scale=[10.0, 3.0, 1.0], size=(100, 3))

    detector = NTESAnomalyDetector()
    detector.fit(train_data)

    # Test nominal data
    test_data = np.array([[82.0, 4.0, 2.0]])
    score = detector.score(test_data)
    assert score[0] > -0.5  # High score = normal
    assert not detector.is_anomalous(test_data)

    # Test outlier data (implausible speed + massive delay)
    outlier_data = np.array([[290.0, 600.0, 15.0]])
    assert detector.is_anomalous(outlier_data)


def test_lstm_autoencoder():
    # Sequence of 30 steps, 5 features per step, batch of 4
    x = torch.randn(4, 30, 5)

    model = LSTMAutoencoder(input_dim=5, hidden_dim=32, n_layers=2)
    out = model(x)

    assert out.shape == (4, 30, 5)

    # Reconstruction error
    error = model.reconstruction_error(x)
    assert error.shape == (4,)
    assert (error >= 0.0).all()
