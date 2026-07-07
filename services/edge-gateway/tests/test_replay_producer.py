"""Replay producer — JSONL to Redpanda."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

from verge_edge.replay_producer import publish_jsonl


def test_publish_jsonl_produces_each_line(tmp_path):
    path = tmp_path / "events.jsonl"
    events = [{"type": "reading", "ts": "2025-01-01T00:00:00", "sensorId": "S1"},
              {"type": "reading", "ts": "2025-01-01T00:01:00", "sensorId": "S2"}]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    mock_producer = MagicMock()
    fake_kafka = MagicMock()
    fake_kafka.Producer.return_value = mock_producer
    with patch.dict(sys.modules, {"confluent_kafka": fake_kafka}):
        rc = publish_jsonl(path, brokers="localhost:19092", topic="verge.events")

    assert rc == 0
    assert mock_producer.produce.call_count == 2
    mock_producer.flush.assert_called_once()


def test_publish_jsonl_missing_file(tmp_path):
    fake_kafka = MagicMock()
    with patch.dict(sys.modules, {"confluent_kafka": fake_kafka}):
        rc = publish_jsonl(tmp_path / "missing.jsonl", brokers="localhost:19092")
    assert rc == 1
