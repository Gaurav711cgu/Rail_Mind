import pytest
from app.services.dlq_handler import DeadLetterQueueHandler
from app.services.backpressure_controller import BackpressureController
from app.services.outbox import TransactionalOutbox

def test_dlq_handler_routes_poison_messages():
    handler = DeadLetterQueueHandler(max_retries=3)
    raw_msg = b'{"bad_json": true}'
    dlq_event = handler.handle_poison_message(raw_msg, "Corrupted telemetry schema", "railmind-telemetry", 0, 105, 1)
    
    assert dlq_event["dlq_topic"] == "railmind-telemetry-dlq"
    assert dlq_event["original_offset"] == 105
    assert dlq_event["retry_count"] == 1
    assert len(handler.dead_letters) == 1

def test_backpressure_controller_pause_resume():
    controller = BackpressureController(high_watermark_lag=5000, low_watermark_lag=1000)
    
    res1 = controller.evaluate_lag(3000)
    assert res1["action"] == "NONE"
    assert not controller.is_paused

    res2 = controller.evaluate_lag(5500)
    assert res2["action"] == "PAUSE"
    assert controller.is_paused

    res3 = controller.evaluate_lag(800)
    assert res3["action"] == "RESUME"
    assert not controller.is_paused

def test_transactional_outbox_staging_and_relay():
    outbox = TransactionalOutbox()
    entry = outbox.stage_event("siding_hold", "SIDING_101", "HOLD_UPDATED", {"train_id": "12626", "delay_min": 12.5})
    
    assert entry["status"] == "PENDING"
    assert len(outbox.pending_outbox_events) == 1

    relayed = outbox.relay_pending_events()
    assert len(relayed) == 1
    assert relayed[0]["status"] == "PUBLISHED"
    assert len(outbox.pending_outbox_events) == 0
