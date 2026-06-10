from fastapi import APIRouter, HTTPException, status
from app.models.rac import RACQuery, RACPrediction, FactorImpact
from app.ml.rac_predictor import rac_predictor

router = APIRouter()


@router.post("/predict", response_model=RACPrediction)
async def predict_rac(query: RACQuery):
    try:
        prediction_result = rac_predictor.predict(query)
        factors = [
            FactorImpact(factor=f["factor"], impact=f["impact"])
            for f in prediction_result.get("key_factors", [])
        ]
        return RACPrediction(
            confirmation_probability=prediction_result["confirmation_probability"],
            confidence_interval=prediction_result["confidence_interval"],
            key_factors=factors,
            model_version=prediction_result["model_version"],
            disclaimer=prediction_result["disclaimer"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction engine error: {str(e)}",
        )


@router.get("/model-health")
async def get_model_health():
    return {
        "status": "loaded" if rac_predictor._loaded else "fallback_mode",
        "model_version": "XGBoost-v1.2" if rac_predictor._loaded else "Heuristic-v1.0",
        "has_explainer": rac_predictor._explainer is not None,
        "features_expected": [
            "days_to_journey",
            "current_waitlist_position",
            "current_rac_count",
            "quota",
        ],
    }


@router.get("/historical-trends")
async def get_historical_trends(train_no: str):
    # Mock confirmation trends over the last 6 months for a given train
    import random

    random.seed(train_no)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    base_rate = 0.82 if train_no == "22415" else 0.71 if train_no == "12002" else 0.55
    trends = []
    for m in months:
        # Add a bit of random variance
        variance = (random.random() - 0.5) * 0.1
        trends.append({"month": m, "rate": round(base_rate + variance, 3)})
    return trends


@router.get("/alternative-suggestions")
async def get_alternative_suggestions(
    train_no: str, from_station: str, to_station: str
):
    # Provides alternative train routes and their odds
    if train_no == "12002":
        return [
            {
                "train_no": "22415",
                "train_name": "NDLS-BSB Vande Bharat",
                "departure": "15:00",
                "duration": "1h 20m",
                "confirmation_probability": 0.88,
                "delay_minutes": 0,
                "status": "RUNNING",
            },
            {
                "train_no": "12301",
                "train_name": "Howrah Rajdhani Express",
                "departure": "16:50",
                "duration": "1h 15m",
                "confirmation_probability": 0.94,
                "delay_minutes": 15,
                "status": "DELAYED",
            },
        ]
    else:
        return [
            {
                "train_no": "12002",
                "train_name": "NDLS-BCT Shatabdi Express",
                "departure": "06:00",
                "duration": "1h 22m",
                "confirmation_probability": 0.76,
                "delay_minutes": 40,
                "status": "HELD",
            },
            {
                "train_no": "12301",
                "train_name": "Howrah Rajdhani Express",
                "departure": "16:50",
                "duration": "1h 15m",
                "confirmation_probability": 0.94,
                "delay_minutes": 15,
                "status": "DELAYED",
            },
        ]


@router.get("/quota-heatmap")
async def get_quota_heatmap(train_no: str, waitlist_pos: int):
    # Returns a comparison of odds across quotas
    base_odds = 0.85 if train_no == "22415" else 0.70
    decay = waitlist_pos * 0.02

    return [
        {
            "quota": "GN (General)",
            "probability": max(0.05, round(base_odds - decay, 3)),
            "description": "Standard booking bucket",
        },
        {
            "quota": "TQ (Tatkal)",
            "probability": max(0.02, round(base_odds * 0.6 - decay, 3)),
            "description": "Last minute allocation",
        },
        {
            "quota": "LD (Ladies)",
            "probability": max(0.1, round(base_odds * 1.1 - decay, 3)),
            "description": "Reserved ladies allocation",
        },
        {
            "quota": "DF (Defense)",
            "probability": max(0.2, round(base_odds * 1.25 - decay, 3)),
            "description": "Military personnel quota",
        },
    ]
