"""Frozen non-environment schema shared by the Gate and Worker manifest."""

BOARD_PUBLISH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "revises",
        "client_ref",
        "kind",
        "assertion_role",
        "text",
        "structured_assertion",
        "basis_refs",
        "limitations",
    ],
    "properties": {
        "revises": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["entity_type", "id", "revision"],
                    "properties": {
                        "entity_type": {"type": "string", "const": "claim"},
                        "id": {"type": "string", "minLength": 1, "maxLength": 256},
                        "revision": {"type": "string", "pattern": "^(0|[1-9][0-9]*)$"},
                    },
                },
                {"type": "null"},
            ]
        },
        "client_ref": {"type": "string", "minLength": 1, "maxLength": 256},
        "kind": {
            "type": "string",
            "enum": ["observation-summary", "hypothesis", "derived-conclusion"],
        },
        "assertion_role": {
            "type": "string",
            "enum": ["candidate_fact", "explanation", "hypothesis"],
        },
        "text": {"type": "string", "minLength": 1, "maxLength": 32768},
        "structured_assertion": {"anyOf": [{"type": "object"}, {"type": "null"}]},
        "basis_refs": {
            "type": "array",
            "maxItems": 256,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["entity_type", "id", "revision"],
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["claim", "observation", "artifact", "intent"],
                    },
                    "id": {"type": "string", "minLength": 1, "maxLength": 256},
                    "revision": {"type": "string", "pattern": "^(0|[1-9][0-9]*)$"},
                },
            },
        },
        "limitations": {
            "type": "array",
            "maxItems": 128,
            "items": {"type": "string", "minLength": 1, "maxLength": 1024},
        },
    },
}
