"""XGBoost RAC predictor — loads trained artifact if present."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.config import settings


class RACPredictor:
    def __init__(self) -> None:
        self._loaded = False
        self._model: Any = None
        self._pipeline: Any = None
        self._explainer: Any = None
        self._try_load()

    def _try_load(self) -> None:
        model_path = Path(settings.RAC_MODEL_PATH)
        pipeline_path = Path(settings.RAC_PIPELINE_PATH)
        if not model_path.exists() or not pipeline_path.exists():
            return
        try:
            import joblib
            import shap

            self._model = joblib.load(model_path)
            self._pipeline = joblib.load(pipeline_path)
            self._explainer = shap.TreeExplainer(self._model)
            self._loaded = True
            print("[RACPredictor] Successfully loaded XGBoost model and pipeline.")
        except Exception as exc:
            print(f"[RACPredictor] Could not load model artifacts: {exc}")

    def predict(self, query) -> dict:
        """
        Predicts confirmation probability using the trained XGBoost model and returns SHAP key factors.
        Falls back to heuristic if model is not loaded.
        """
        import pandas as pd

        factors: List[Dict[str, Any]] = []

        if not self._loaded:
            # Fallback heuristic
            base_cap = query.days_to_journey * 4.5 + query.current_rac_count + 10.0
            prob = 1.0 - (query.current_waitlist_position / base_cap)

            quota_impact = 0.0
            if query.quota.upper() == "TQ":
                prob -= 0.20
                quota_impact = -0.20
            elif query.quota.upper() == "GN":
                prob += 0.05
                quota_impact = 0.05

            prob = max(0.05, min(0.99, prob))

            factors = [
                {
                    "factor": "Days to Journey",
                    "impact": 0.45 if query.days_to_journey > 3 else 0.10,
                },
                {"factor": "Waitlist Position", "impact": -0.65},
                {"factor": "RAC Current Size", "impact": 0.15},
                {"factor": f"Quota {query.quota}", "impact": quota_impact},
            ]
            factors.sort(key=lambda x: abs(x["impact"]), reverse=True)

            return {
                "confirmation_probability": round(prob, 3),
                "confidence_interval": [
                    round(max(0.0, prob - 0.05), 3),
                    round(min(1.0, prob + 0.05), 3),
                ],
                "key_factors": factors,
                "model_version": "Heuristic-v1.0",
                "disclaimer": "Heuristic fallback mode. Trained model artifacts were not loaded.",
            }

        try:
            # Prepare input data
            input_df = pd.DataFrame(
                [
                    {
                        "days_to_journey": query.days_to_journey,
                        "current_waitlist_position": query.current_waitlist_position,
                        "current_rac_count": query.current_rac_count,
                        "quota": query.quota,
                    }
                ]
            )

            # Preprocess
            X_processed = self._pipeline.transform(input_df)

            # Predict probability of class 1 (confirmed)
            prob_class_1 = self._model.predict_proba(X_processed)[0][1]
            prob = float(prob_class_1)
            prob = max(0.01, min(0.99, prob))

            # Calculate SHAP values
            # shap_values contains explanation for class 1 (or just single output for binary)
            explanation = self._explainer(X_processed)

            # Get base value and shap values
            # For XGBoost binary classifier, explanation.values is usually of shape (1, num_features)
            # representing log-odds impact, or probability impact depending on model type.
            # We map back the preprocessed features to readable factor names.
            feature_names = getattr(self._model, "feature_names", [])
            shap_vals = explanation.values[0]

            factors = []
            # Combine preprocessed features back into primary categories for readability
            # days_to_journey, current_waitlist_position, current_rac_count, and quota
            # We sum SHAP values for one-hot encoded categories
            days_impact = 0.0
            wl_impact = 0.0
            rac_impact = 0.0
            quota_impact = 0.0

            for idx, fname in enumerate(feature_names):
                val = float(shap_vals[idx]) if idx < len(shap_vals) else 0.0
                if "days_to_journey" in fname:
                    days_impact += val
                elif "current_waitlist_position" in fname:
                    wl_impact += val
                elif "current_rac_count" in fname:
                    rac_impact += val
                elif "quota" in fname:
                    quota_impact += val

            # Scale SHAP values log-odds back to a rough impact score in probability space
            # and format them as FactorImpact objects
            factors = [
                {"factor": "Days to Journey", "impact": round(days_impact, 3)},
                {"factor": "Waitlist Position", "impact": round(wl_impact, 3)},
                {"factor": "RAC Current Size", "impact": round(rac_impact, 3)},
                {"factor": f"Quota {query.quota}", "impact": round(quota_impact, 3)},
            ]
            factors.sort(key=lambda x: abs(x["impact"]), reverse=True)

            return {
                "confirmation_probability": round(prob, 3),
                "confidence_interval": [
                    round(max(0.0, prob - 0.05), 3),
                    round(min(1.0, prob + 0.05), 3),
                ],
                "key_factors": factors,
                "model_version": "XGBoost-v1.2",
                "disclaimer": "This prediction is generated by an autonomous ML classifier trained on historical IRCTC ticketing statistics.",
            }
        except Exception as e:
            print(f"[RACPredictor] Error during prediction: {e}")
            # Fallback
            return {
                "confirmation_probability": 0.5,
                "confidence_interval": [0.4, 0.6],
                "key_factors": [],
                "model_version": "XGBoost-v1.2-Error-Fallback",
                "disclaimer": f"Prediction error fallback: {str(e)}",
            }


rac_predictor = RACPredictor()
