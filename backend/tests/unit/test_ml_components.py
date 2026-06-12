"""
Unit tests for ML components: ensemble_rac, gnn_cascade, railgym.
All tests use small synthetic data to keep CI fast.
"""

import pytest
import numpy as np
import pandas as pd
import torch


# ─────────────────────────────────────────────────────────────
#  compute_ece
# ─────────────────────────────────────────────────────────────


def test_compute_ece_perfect_calibration():
    from app.ml.ensemble_rac import compute_ece

    # Perfect calibration: predicted probs == actual frequencies
    y_true = np.array([1, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.9, 0.8, 0.1, 0.2, 0.7, 0.3, 0.75, 0.25])
    ece = compute_ece(y_true, y_prob, n_bins=5)
    assert 0.0 <= ece <= 1.0


def test_compute_ece_all_wrong():
    from app.ml.ensemble_rac import compute_ece

    y_true = np.ones(100)
    y_prob = np.zeros(100)  # predicts 0 for all 1s
    ece = compute_ece(y_true, y_prob, n_bins=10)
    assert ece > 0.5


def test_compute_ece_uniform_probs():
    from app.ml.ensemble_rac import compute_ece

    rng = np.random.default_rng(42)
    y_true = rng.integers(0, 2, size=200)
    y_prob = np.full(200, 0.5)
    ece = compute_ece(y_true, y_prob)
    assert 0.0 <= ece <= 1.0


# ─────────────────────────────────────────────────────────────
#  get_base_estimators
# ─────────────────────────────────────────────────────────────


def test_get_base_estimators_returns_list():
    from app.ml.ensemble_rac import get_base_estimators

    estimators = get_base_estimators()
    assert len(estimators) >= 2
    for name, est in estimators:
        assert isinstance(name, str)
        assert hasattr(est, "fit")


# ─────────────────────────────────────────────────────────────
#  SequentialStackingClassifier
# ─────────────────────────────────────────────────────────────


def test_stacking_classifier_fit_predict():
    from app.ml.ensemble_rac import SequentialStackingClassifier, get_base_estimators
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.random((100, 5)), columns=[f"f{i}" for i in range(5)])
    y = rng.integers(0, 2, size=100)

    clf = SequentialStackingClassifier(
        estimators=get_base_estimators(),
        final_estimator=LogisticRegression(),
        cv=3,
    )
    clf.fit(X, y)
    preds = clf.predict(X)
    assert len(preds) == 100
    assert set(preds).issubset({0, 1})


def test_stacking_classifier_predict_proba():
    from app.ml.ensemble_rac import SequentialStackingClassifier, get_base_estimators
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.random((80, 4)), columns=[f"f{i}" for i in range(4)])
    y = rng.integers(0, 2, size=80)

    clf = SequentialStackingClassifier(
        estimators=get_base_estimators(),
        final_estimator=LogisticRegression(),
        cv=3,
    )
    clf.fit(X, y)
    proba = clf.predict_proba(X)
    assert proba.shape == (80, 2)
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)


# ─────────────────────────────────────────────────────────────
#  EnsembleRACPredictor
# ─────────────────────────────────────────────────────────────


def _make_rac_dataset(n=120, seed=42):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        {
            "waitlist_position": rng.integers(1, 100, size=n),
            "rac_count": rng.integers(0, 60, size=n),
            "days_to_journey": rng.integers(1, 90, size=n),
            "quota_code": rng.integers(0, 4, size=n),
            "train_type_code": rng.integers(0, 5, size=n),
        }
    )
    y = ((X["waitlist_position"] < 20) & (X["days_to_journey"] > 7)).astype(int).values
    return X, y


def test_ensemble_predictor_fit_and_predict_proba():
    from app.ml.ensemble_rac import EnsembleRACPredictor

    X, y = _make_rac_dataset(120)
    predictor = EnsembleRACPredictor(n_bins=5)
    predictor.fit(X, y)
    proba = predictor.predict_proba(X.iloc[:10])
    assert len(proba) == 10
    assert all(0.0 <= p <= 1.0 for p in proba)


def test_ensemble_predictor_raises_if_not_fitted():
    from app.ml.ensemble_rac import EnsembleRACPredictor

    predictor = EnsembleRACPredictor()
    X = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(RuntimeError, match="not fitted"):
        predictor.predict_proba(X)


def test_ensemble_predictor_evaluate():
    from app.ml.ensemble_rac import EnsembleRACPredictor

    X, y = _make_rac_dataset(150)
    predictor = EnsembleRACPredictor(n_bins=5)
    predictor.fit(X, y)
    metrics = predictor.evaluate(X, y)
    assert "auc" in metrics or "roc_auc" in metrics or "accuracy" in metrics


# ─────────────────────────────────────────────────────────────
#  RailwayGNN
# ─────────────────────────────────────────────────────────────


def test_railway_gnn_forward_pass():
    from app.ml.gnn_cascade import RailwayGNN

    model = RailwayGNN(node_features=8, hidden_dim=32, num_layers=2)
    # Minimal graph: 5 nodes, 4 edges
    x = torch.randn(5, 8)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
    edge_attr = torch.randn(4, 4)
    out = model(x, edge_index, edge_attr)
    assert out.shape[0] == 5
    assert not torch.isnan(out).any()


def test_railway_gnn_single_node():
    from app.ml.gnn_cascade import RailwayGNN

    model = RailwayGNN(node_features=8, hidden_dim=16, num_layers=1)
    x = torch.randn(1, 8)
    edge_index = torch.zeros((2, 0), dtype=torch.long)
    edge_attr = torch.zeros((0, 4))
    out = model(x, edge_index, edge_attr)
    assert out.shape[0] == 1


def test_cascade_loss_forward():
    from app.ml.gnn_cascade import CascadeLoss

    loss_fn = CascadeLoss(alpha=0.7, beta=0.3)
    predictions = torch.sigmoid(torch.randn(10))
    targets = torch.randint(0, 2, (10,)).float()
    cascade_weights = torch.rand(10)
    loss = loss_fn(predictions, targets, cascade_weights)
    assert loss.item() >= 0.0
    assert not torch.isnan(loss)


# ─────────────────────────────────────────────────────────────
#  RailGym
# ─────────────────────────────────────────────────────────────


def test_railgym_reset():
    from app.ml.railgym import RailGym

    env = RailGym(scenario="normal")
    obs, info = env.reset(seed=42)
    assert obs.shape == (RailGym.N_SECTIONS * 7,)
    assert obs.dtype == np.float32
    assert isinstance(info, dict)


def test_railgym_step():
    from app.ml.railgym import RailGym

    env = RailGym(scenario="moderate")
    env.reset(seed=0)
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == (RailGym.N_SECTIONS * 7,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)


def test_railgym_full_episode():
    from app.ml.railgym import RailGym

    env = RailGym(scenario="severe")
    obs, _ = env.reset(seed=7)
    total_reward = 0.0
    steps = 0
    terminated = False
    while not terminated:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
        if steps > 100:
            break
    assert steps == env._max_steps or terminated


def test_railgym_scenarios():
    from app.ml.railgym import RailGym

    for scenario in ["normal", "moderate", "severe", "fog"]:
        env = RailGym(scenario=scenario)
        obs, _ = env.reset(seed=1)
        assert obs is not None


def test_railgym_observation_space_valid():
    from app.ml.railgym import RailGym

    env = RailGym()
    obs, _ = env.reset()
    assert env.observation_space.contains(obs)


def test_railgym_action_space_shape():
    from app.ml.railgym import RailGym

    env = RailGym()
    assert env.action_space.shape == (RailGym.N_SECTIONS,)


def test_train_rac_model():
    from unittest.mock import patch
    from app.ml.train_rac_model import train_and_save_model, generate_synthetic_data

    df = generate_synthetic_data(10)
    assert len(df) == 10
    assert "confirmed" in df.columns

    with patch("joblib.dump") as mock_dump, patch("pathlib.Path.mkdir") as mock_mkdir:
        train_and_save_model()
        mock_mkdir.assert_called()
        assert mock_dump.call_count == 2


def test_ensemble_predict_proba_no_frozen_estimator_error():
    """
    Regression test: CalibratedClassifierCV(cv='prefit') on a StackingClassifier
    raised 'FrozenEstimator should be a classifier' on sklearn>=1.6.
    Fix: calibrate base estimators individually, stack without post-hoc calibration.
    """
    from app.ml.ensemble_rac import EnsembleRACPredictor
    X, y = _make_rac_dataset(100)
    predictor = EnsembleRACPredictor()
    predictor.fit(X, y)
    probs = predictor.predict_proba(X.iloc[:10])
    assert probs.shape == (10,)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
