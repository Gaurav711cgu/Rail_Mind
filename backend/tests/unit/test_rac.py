from app.models.rac import RACQuery
from app.ml.rac_predictor import rac_predictor


def test_rac_predictor_loaded():
    # Model should be loaded because we ran training first
    assert rac_predictor._loaded is True
    assert rac_predictor._model is not None
    assert rac_predictor._pipeline is not None
    assert rac_predictor._explainer is not None


def test_rac_prediction_success():
    query = RACQuery(
        train_no="12002",
        from_station="NDLS",
        to_station="CNB",
        date="2026-06-12",
        current_waitlist_position=10,
        current_rac_count=20,
        days_to_journey=5,
        quota="GN",
    )
    result = rac_predictor.predict(query)
    assert "confirmation_probability" in result
    assert 0.0 <= result["confirmation_probability"] <= 1.0
    assert len(result["key_factors"]) == 4
    assert result["model_version"] == "XGBoost-v1.2"


def test_rac_prediction_boundary_conditions():
    # Test very high waitlist position (probability should be low)
    query_low = RACQuery(
        train_no="12002",
        from_station="NDLS",
        to_station="CNB",
        date="2026-06-12",
        current_waitlist_position=500,
        current_rac_count=0,
        days_to_journey=1,
        quota="TQ",
    )
    result_low = rac_predictor.predict(query_low)

    # Test low waitlist position, far out (probability should be high)
    query_high = RACQuery(
        train_no="12002",
        from_station="NDLS",
        to_station="CNB",
        date="2026-06-12",
        current_waitlist_position=2,
        current_rac_count=40,
        days_to_journey=40,
        quota="GN",
    )
    result_high = rac_predictor.predict(query_high)

    assert result_high["confirmation_probability"] > result_low["confirmation_probability"]
