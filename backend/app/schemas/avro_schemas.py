"""
Apache Avro schemas for RailMind event-driven topics.
"""

import json

TRAIN_POSITION_EVENT_SCHEMA = {
    "type": "record",
    "name": "TrainPositionEvent",
    "namespace": "com.railmind.events",
    "fields": [
        {"name": "train_no", "type": "string"},
        {"name": "station_code", "type": "string"},
        {"name": "delay_minutes", "type": "int"},
        {"name": "data_quality", "type": "float"},
        {"name": "anomaly_flag", "type": ["null", "string"], "default": None},
        {
            "name": "source",
            "type": {"type": "enum", "name": "Source", "symbols": ["NTES", "RAPIDAPI", "CACHE"]},
        },
        {"name": "event_time", "type": "long"},
    ],
}

DISRUPTION_EVENT_SCHEMA = {
    "type": "record",
    "name": "DisruptionEvent",
    "namespace": "com.railmind.events",
    "fields": [
        {"name": "disruption_id", "type": "string"},
        {"name": "train_no", "type": "string"},
        {"name": "section_from", "type": "string"},
        {"name": "section_to", "type": "string"},
        {"name": "disruption_type", "type": "string"},
        {"name": "severity", "type": "string"},
        {"name": "cascade_depth", "type": "int"},
        {"name": "event_time", "type": "long"},
    ],
}

RECOMMENDATION_EVENT_SCHEMA = {
    "type": "record",
    "name": "RecommendationEvent",
    "namespace": "com.railmind.events",
    "fields": [
        {"name": "recommendation_id", "type": "string"},
        {"name": "disruption_id", "type": "string"},
        {
            "name": "type",
            "type": {
                "type": "enum",
                "name": "RecType",
                "symbols": ["HOLD", "PROCEED", "REROUTE_FREIGHT", "ESCALATE"],
            },
        },
        {"name": "target_train", "type": "string"},
        {"name": "confidence", "type": "float"},
        {"name": "tier", "type": "int"},
        {"name": "reasoning", "type": "string"},
        {"name": "is_approved", "type": "boolean"},
        {"name": "event_time", "type": "long"},
    ],
}

AUDIT_EVENT_SCHEMA = {
    "type": "record",
    "name": "AuditEvent",
    "namespace": "com.railmind.events",
    "fields": [
        {"name": "audit_id", "type": "string"},
        {"name": "actor", "type": "string"},
        {"name": "action", "type": "string"},
        {"name": "hash", "type": "string"},
        {"name": "prev_hash", "type": "string"},
        {"name": "metadata_json", "type": "string"},
        {"name": "event_time", "type": "long"},
    ],
}


def get_schema_json(schema_dict: dict) -> str:
    """Returns the JSON string representation of the Avro schema."""
    return json.dumps(schema_dict)
