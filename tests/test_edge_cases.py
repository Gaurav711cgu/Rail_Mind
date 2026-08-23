import pytest
from app.rac_predictor import predict_rac_probability

def test_invalid_train_number():
    with pytest.raises(ValueError):
        predict_rac_probability("999999", "2026-10-10")

def test_past_date_prediction():
    # Should handle past dates gracefully (e.g. historical data check)
    result = predict_rac_probability("12345", "2020-01-01")
    assert "error" in result or result.get("historical") is True

def test_malformed_date_format():
    with pytest.raises(ValueError):
        predict_rac_probability("12345", "10-10-2026")
