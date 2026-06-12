"""
Ensemble RAC Predictor — Stacking Classifier with Isotonic Probability Calibration.
Includes expected calibration error (ECE) calculations and robust fallback estimators.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.model_selection import KFold
import sys

# Base imports with fallback options
# Enforce fallback on macOS to prevent OpenMP duplicate library conflicts with PyTorch
FORCE_FALLBACK = sys.platform == "darwin"

if FORCE_FALLBACK:
    HAS_XGB = False
    HAS_LGB = False
    HAS_CAT = False
else:
    try:
        import xgboost as xgb

        HAS_XGB = True
    except ImportError:
        HAS_XGB = False

    try:
        import lightgbm as lgb

        HAS_LGB = True
    except ImportError:
        HAS_LGB = False

    try:
        from catboost import CatBoostClassifier

        HAS_CAT = True
    except ImportError:
        HAS_CAT = False


def get_base_estimators():
    """Returns base estimators; falls back to sklearn models if advanced packages are missing."""
    estimators = []

    if HAS_XGB:
        estimators.append(
            (
                "xgb",
                xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    eval_metric="logloss",
                    n_jobs=1,
                ),
            )
        )
    else:
        estimators.append(
            (
                "gb_default",
                GradientBoostingClassifier(n_estimators=100, max_depth=6, learning_rate=0.05),
            )
        )

    if HAS_LGB:
        estimators.append(
            (
                "lgb",
                lgb.LGBMClassifier(
                    n_estimators=100,
                    num_leaves=31,
                    learning_rate=0.05,
                    feature_fraction=0.8,
                    bagging_fraction=0.8,
                    verbosity=-1,
                    n_jobs=1,
                ),
            )
        )
    else:
        estimators.append(("rf_default", RandomForestClassifier(n_estimators=100, max_depth=6)))

    if HAS_CAT:
        estimators.append(
            (
                "cat",
                CatBoostClassifier(
                    iterations=100, depth=6, learning_rate=0.05, verbose=0, thread_count=1
                ),
            )
        )
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier

        estimators.append(
            (
                "hgb_default",
                HistGradientBoostingClassifier(max_iter=100, max_depth=6, learning_rate=0.05),
            )
        )

    return estimators


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE) for binary classification.

    ECE = sum( (bin_size / total) * abs(bin_acc - bin_conf) )
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece_val = 0.0
    n_samples = len(y_true)

    for low, high in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= low) & (y_prob < high)
        bin_size = np.sum(mask)
        if bin_size == 0:
            continue

        bin_acc = np.mean(y_true[mask])
        bin_conf = np.mean(y_prob[mask])
        ece_val += (bin_size / n_samples) * abs(bin_acc - bin_conf)

    return ece_val


class SequentialStackingClassifier(ClassifierMixin, BaseEstimator):
    """
    A sequential StackingClassifier that does not use joblib or multiprocessing.
    This prevents macOS OpenMP/multiprocessing crashes when running alongside PyTorch.
    """

    def __init__(self, estimators, final_estimator, cv=5):
        self.estimators = estimators
        self.final_estimator = final_estimator
        self.cv = cv
        self.fitted_estimators_ = []
        self.classes_ = None

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.fitted_estimators_ = []

        # Fit base estimators on the full training set
        for name, est in self.estimators:
            fitted_est = clone(est).fit(X, y)
            self.fitted_estimators_.append(fitted_est)

        # Fit final estimator (meta-learner) using sequential K-Fold out-of-fold predictions
        kf = KFold(n_splits=self.cv, shuffle=True, random_state=42)
        X_np = X.to_numpy() if isinstance(X, pd.DataFrame) else np.array(X)
        y_np = np.array(y)

        oof_preds = np.zeros((len(X_np), len(self.estimators)))

        for train_idx, val_idx in kf.split(X_np):
            X_tr, X_val = X_np[train_idx], X_np[val_idx]
            y_tr, _ = y_np[train_idx], y_np[val_idx]

            for j, (name, est) in enumerate(self.estimators):
                fold_est = clone(est).fit(X_tr, y_tr)
                oof_preds[val_idx, j] = fold_est.predict_proba(X_val)[:, 1]

        self.final_estimator.fit(oof_preds, y_np)
        return self

    def predict_proba(self, X):
        X_np = X.to_numpy() if isinstance(X, pd.DataFrame) else np.array(X)
        meta_features = np.zeros((len(X_np), len(self.fitted_estimators_)))
        for j, est in enumerate(self.fitted_estimators_):
            meta_features[:, j] = est.predict_proba(X_np)[:, 1]
        return self.final_estimator.predict_proba(meta_features)

    def predict(self, X):
        X_np = X.to_numpy() if isinstance(X, pd.DataFrame) else np.array(X)
        meta_features = np.zeros((len(X_np), len(self.fitted_estimators_)))
        for j, est in enumerate(self.fitted_estimators_):
            meta_features[:, j] = est.predict_proba(X_np)[:, 1]
        return self.final_estimator.predict(meta_features)


class EnsembleRACPredictor:
    """
    Calibrated Stacked Ensemble RAC confirmation predictor.
    Uses StackingClassifier with LogisticRegression meta-learner.
    """

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self.base_estimators = get_base_estimators()
        self.meta_learner = LogisticRegression(C=0.1)
        
        # Calibrate EACH base estimator individually via cross-validation
        self.calibrated_bases = []
        for name, est in self.base_estimators:
            calibrated = CalibratedClassifierCV(est, method="isotonic", cv=3)
            self.calibrated_bases.append((name, calibrated))

        self.stacking_clf = SequentialStackingClassifier(
            estimators=self.calibrated_bases,
            final_estimator=self.meta_learner,
            cv=5,
        )
        self._is_fitted = False

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """Fits base stacking classifier."""
        print("Training base stacked ensemble classifier...")
        self.stacking_clf.fit(X, y)
        self._is_fitted = True

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts calibrated confirmation probabilities."""
        if not self._is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.stacking_clf.predict_proba(X)[:, 1]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Returns binary confirmation predictions (threshold=0.5)."""
        if not self._is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.stacking_clf.predict(X)

    def evaluate(self, X_test: pd.DataFrame, y_test: np.ndarray) -> dict:
        """Returns standard metrics + calibration ECE score."""
        probs = self.predict_proba(X_test)
        preds = self.predict(X_test)

        from sklearn.metrics import roc_auc_score, log_loss, accuracy_score

        auc = roc_auc_score(y_test, probs)
        loss = log_loss(y_test, probs)
        acc = accuracy_score(y_test, preds)
        ece_score = compute_ece(y_test, probs, n_bins=self.n_bins)

        return {"accuracy": acc, "roc_auc": auc, "log_loss": loss, "ece": ece_score}
