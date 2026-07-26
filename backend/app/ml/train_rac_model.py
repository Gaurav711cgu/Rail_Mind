from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import joblib
from app.config import settings


def generate_synthetic_data(num_rows: int = 5000) -> pd.DataFrame:
    np.random.seed(42)

    days_to_journey = np.random.randint(1, 60, size=num_rows)
    current_waitlist_position = np.random.randint(1, 150, size=num_rows)
    current_rac_count = np.random.randint(0, 50, size=num_rows)
    quota = np.random.choice(["GN", "TQ", "LD", "DF"], size=num_rows, p=[0.7, 0.15, 0.1, 0.05])

    # Calculate underlying probability
    # waitlist position decreases confirmation probability
    # days to journey increases it
    # current RAC count increases it
    # quota GN/LD/DF increases it, TQ decreases it
    prob = 0.5 - (current_waitlist_position * 0.005) + (days_to_journey * 0.008) + (current_rac_count * 0.003)

    # Quota modifiers
    quota_mods = {"GN": 0.05, "TQ": -0.20, "LD": 0.10, "DF": 0.15}
    for q, mod in quota_mods.items():
        prob[quota == q] += mod

    # Add noise
    prob += np.random.normal(0, 0.05, size=num_rows)
    prob = np.clip(prob, 0.01, 0.99)

    confirmed = (prob > 0.5).astype(int)

    df = pd.DataFrame(
        {
            "days_to_journey": days_to_journey,
            "current_waitlist_position": current_waitlist_position,
            "current_rac_count": current_rac_count,
            "quota": quota,
            "confirmed": confirmed,
        }
    )
    return df


def train_and_save_model():
    df = generate_synthetic_data(5000)
    X = df.drop(columns=["confirmed"])
    y = df["confirmed"]

    numeric_features = [
        "days_to_journey",
        "current_waitlist_position",
        "current_rac_count",
    ]
    categorical_features = ["quota"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

    pipeline = Pipeline(steps=[("preprocessor", preprocessor)])

    X_processed = pipeline.fit_transform(X)

    # Get feature names after preprocessing for SHAP compatibility
    cat_encoder = pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    cat_feature_names = list(cat_encoder.get_feature_names_out(categorical_features))
    feature_names = numeric_features + cat_feature_names

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
    )

    model.fit(X_processed, y)

    # Save the pipeline and model
    artifacts_dir = Path(__file__).parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_dir / "rac_model.joblib"
    pipeline_path = artifacts_dir / "feature_pipeline.joblib"

    # Store feature names in model to easily retrieve later
    model.feature_names = feature_names

    joblib.dump({"model": model, "version": settings.RAC_MODEL_VERSION}, model_path)
    joblib.dump(pipeline, pipeline_path)
    print(f"Model saved to {model_path}")
    print(f"Pipeline saved to {pipeline_path}")


if __name__ == "__main__":
    train_and_save_model()
