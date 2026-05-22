#!/usr/bin/env python3
"""Unit tests for dnsx conversion, correlation, and ingestion."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONVERTER = ROOT / "convert3rs" / "dnsx" / "convert3r_dnsx.py"
INGESTOR = Path(__file__).with_name("ingest3r_dnsx.py")
CORRELATION = Path(__file__).with_name("correlation_engine.py")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def install_fake_qdrant_modules() -> None:
    class Distance:
        COSINE = "Cosine"

    class VectorParams:
        def __init__(self, size, distance):
            self.size = size
            self.distance = distance

    class PayloadSchemaType:
        KEYWORD = "keyword"

    class PointStruct:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload

    class MatchValue:
        def __init__(self, value):
            self.value = value

    class FieldCondition:
        def __init__(self, key, match):
            self.key = key
            self.match = match

    class Filter:
        def __init__(self, must):
            self.must = must

    fake_models = SimpleNamespace(
        Distance=Distance,
        VectorParams=VectorParams,
        PayloadSchemaType=PayloadSchemaType,
        PointStruct=PointStruct,
        MatchValue=MatchValue,
        FieldCondition=FieldCondition,
        Filter=Filter,
    )
    fake_qdrant = SimpleNamespace(QdrantClient=object, models=fake_models)
    sys.modules["qdrant_client"] = fake_qdrant
    sys.modules["qdrant_client.http"] = SimpleNamespace(models=fake_models)


def test_convert_dnsx_jsonl_normalizes_records():
    converter = load_module("convert3r_dnsx_test", CONVERTER)
    lines = [
        '{"host":"www.example.com","a":"93.184.216.34","resolver":"1.1.1.1:53","status_code":"NOERROR"}',
        "",
        "not json",
        '["not-object"]',
    ]

    records, skipped = converter.convert_dnsx_jsonl(lines, timestamp="2026-01-01T00:00:00Z")

    assert skipped == 3
    assert len(records) == 1
    assert records[0]["id"] == 1
    assert records[0]["host"] == "www.example.com"
    assert records[0]["a"] == ["93.184.216.34"]
    assert records[0]["resolver"] == ["1.1.1.1:53"]
    assert records[0]["raw_response"]["host"] == "www.example.com"


def test_correlation_matches_current_subfinder_hostname_payload():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_test", CORRELATION)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name="Subfinder_json")])
    client.scroll.return_value = ([SimpleNamespace(id=42, payload={"hostname": "www.example.com"})], None)

    engine = correlation.DNSCorrelationEngine(client, collections=["Subfinder_json"])
    record = engine.correlate_dns_record({"id": 1, "host": "www.example.com", "a": ["93.184.216.34"]})

    assert record["correlation_status"] == "matched"
    assert record["linked_subdomain_id"] == 42
    assert record["linked_collection"] == "Subfinder_json"
    assert record["resolved_ips"] == ["93.184.216.34"]


def test_correlation_updates_linked_subdomain_payload():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_update_test", CORRELATION)
    client = MagicMock()
    engine = correlation.DNSCorrelationEngine(client, collections=[])

    ok = engine.update_subdomain_with_dns_info(
        {
            "id": 9,
            "timestamp": "2026-01-01T00:00:00Z",
            "correlation_status": "matched",
            "linked_subdomain_id": 42,
            "linked_collection": "Subfinder_json",
            "a": ["93.184.216.34"],
            "aaaa": ["2001:db8::1"],
        }
    )

    assert ok is True
    client.set_payload.assert_called_once()
    payload = client.set_payload.call_args.kwargs["payload"]
    assert payload["latest_dns_record_id"] == 9
    assert payload["resolved_ips"] == ["93.184.216.34"]
    assert payload["resolved_ipv6"] == ["2001:db8::1"]


def test_ingestor_uploads_without_correlation():
    install_fake_qdrant_modules()
    ingestor_mod = load_module("dnsx_ingestor_test", INGESTOR)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[])
    client.count.return_value = SimpleNamespace(count=0)

    ingestor = ingestor_mod.DNSxIngestor(client, "dnsx_records", vector_size=8)
    stats = ingestor.ingest_records([{"id": 1, "host": "www.example.com", "a": ["93.184.216.34"]}], batch_size=100)

    assert stats == {"total": 1, "inserted": 1, "updated": 0, "correlated": 0, "errors": 0}
    client.create_collection.assert_called_once()
    client.upsert.assert_called_once()
    point = client.upsert.call_args.kwargs["points"][0]
    assert point.id != 1
    assert len(point.vector) == 8
    assert point.payload["host"] == "www.example.com"
    assert point.payload["normalized_host"] == "www.example.com"


def test_ingestor_reuses_existing_dns_record_id_on_update():
    install_fake_qdrant_modules()
    ingestor_mod = load_module("dnsx_ingestor_update_test", INGESTOR)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name="dnsx_records")])
    client.count.return_value = SimpleNamespace(count=1)
    engine = MagicMock()
    engine.correlate_dns_record.side_effect = lambda record: {**record, "correlation_status": "unmatched"}
    engine.prepare_upsert_operation.return_value = {"operation": "update", "point_id": 99, "record": {}}

    ingestor = ingestor_mod.DNSxIngestor(client, "dnsx_records", vector_size=8)
    stats = ingestor.ingest_records([{"id": 1, "host": "www.example.com"}], correlation_engine=engine)

    assert stats["updated"] == 1
    assert stats["inserted"] == 0
    point = client.upsert.call_args.kwargs["points"][0]
    assert point.id == 99
    assert point.payload["id"] == 99


def test_ingestor_uses_stable_deterministic_id_without_correlation():
    install_fake_qdrant_modules()
    ingestor_mod = load_module("dnsx_ingestor_deterministic_test", INGESTOR)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[])

    ingestor = ingestor_mod.DNSxIngestor(client, "dnsx_records", vector_size=8)
    records = [
        {"id": 1, "host": "WWW.Example.com.", "a": ["93.184.216.34"]},
        {"id": 999, "host": "www.example.com", "a": ["93.184.216.34"]},
    ]

    first = ingestor.ingest_records([records[0]], batch_size=100)
    second = ingestor.ingest_records([records[1]], batch_size=100)

    first_point = client.upsert.call_args_list[-2].kwargs["points"][0]
    second_point = client.upsert.call_args_list[-1].kwargs["points"][0]
    assert first == {"total": 1, "inserted": 1, "updated": 0, "correlated": 0, "errors": 0}
    assert second == {"total": 1, "inserted": 1, "updated": 0, "correlated": 0, "errors": 0}
    assert first_point.id == second_point.id
    assert first_point.id not in {1, 999}
    assert first_point.payload["normalized_host"] == "www.example.com"


def test_linked_subdomain_update_waits_for_successful_dns_upload():
    install_fake_qdrant_modules()
    ingestor_mod = load_module("dnsx_ingestor_deferred_update_test", INGESTOR)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[])
    client.upsert.side_effect = RuntimeError("upsert failed")
    engine = MagicMock()
    engine.correlate_dns_record.side_effect = lambda record: {
        **record,
        "correlation_status": "matched",
        "linked_subdomain_id": 42,
        "linked_collection": "Subfinder_json",
    }
    engine.prepare_upsert_operation.return_value = {"operation": "insert", "point_id": None, "record": {}}

    ingestor = ingestor_mod.DNSxIngestor(client, "dnsx_records", vector_size=8)

    with pytest.raises(RuntimeError, match="upsert failed"):
        ingestor.ingest_records([{"host": "www.example.com"}], correlation_engine=engine, batch_size=100)

    engine.update_subdomain_with_dns_info.assert_not_called()


def test_linked_subdomain_update_runs_after_successful_dns_upload():
    install_fake_qdrant_modules()
    ingestor_mod = load_module("dnsx_ingestor_deferred_update_success_test", INGESTOR)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[])
    engine = MagicMock()
    engine.correlate_dns_record.side_effect = lambda record: {
        **record,
        "correlation_status": "matched",
        "linked_subdomain_id": 42,
        "linked_collection": "Subfinder_json",
    }
    engine.prepare_upsert_operation.return_value = {"operation": "insert", "point_id": None, "record": {}}
    calls = MagicMock()
    calls.attach_mock(client.upsert, "upsert")
    calls.attach_mock(engine.update_subdomain_with_dns_info, "update_subdomain")

    ingestor = ingestor_mod.DNSxIngestor(client, "dnsx_records", vector_size=8)
    ingestor.ingest_records([{"host": "www.example.com"}], correlation_engine=engine, batch_size=100)

    assert client.upsert.called
    engine.update_subdomain_with_dns_info.assert_called_once()
    assert calls.mock_calls[0][0] == "upsert"
    assert calls.mock_calls[1][0] == "update_subdomain"
    updated_record = engine.update_subdomain_with_dns_info.call_args.args[0]
    assert updated_record["id"] == client.upsert.call_args.kwargs["points"][0].id


def test_correlation_normalizes_hostname_for_exact_match():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_normalized_test", CORRELATION)
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name="Subfinder_json")])

    def scroll_side_effect(*, collection_name, scroll_filter, limit, with_payload, with_vectors):
        condition = scroll_filter.must[0]
        if condition.key == "hostname" and condition.match.value == "www.example.com":
            return ([SimpleNamespace(id=42, payload={"hostname": "www.example.com"})], None)
        return ([], None)

    client.scroll.side_effect = scroll_side_effect
    engine = correlation.DNSCorrelationEngine(client, collections=["Subfinder_json"])
    record = engine.correlate_dns_record({"id": 1, "host": " WWW.Example.com. ", "a": ["93.184.216.34"]})

    assert record["correlation_status"] == "matched"
    assert record["normalized_host"] == "www.example.com"
    assert record["linked_subdomain_id"] == 42


def test_correlation_qdrant_collection_failure_is_visible():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_collection_failure_test", CORRELATION)
    client = MagicMock()
    client.get_collections.side_effect = RuntimeError("qdrant unavailable")
    engine = correlation.DNSCorrelationEngine(client, collections=["Subfinder_json"])

    with pytest.raises(RuntimeError, match="qdrant unavailable"):
        engine.find_matching_subdomain("www.example.com")


def test_correlation_scroll_failure_is_visible_for_existing_dns_lookup():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_scroll_failure_test", CORRELATION)
    client = MagicMock()
    client.scroll.side_effect = RuntimeError("bad filter")
    engine = correlation.DNSCorrelationEngine(client, collections=[])

    with pytest.raises(RuntimeError, match="bad filter"):
        engine.find_existing_dns_record("www.example.com")


def test_correlation_finds_existing_dns_record_by_normalized_host():
    install_fake_qdrant_modules()
    correlation = load_module("dnsx_correlation_existing_normalized_test", CORRELATION)
    client = MagicMock()

    def scroll_side_effect(*, collection_name, scroll_filter, limit, with_payload, with_vectors):
        condition = scroll_filter.must[0]
        if condition.key == "normalized_host" and condition.match.value == "www.example.com":
            return ([SimpleNamespace(id=99, payload={"normalized_host": "www.example.com"})], None)
        return ([], None)

    client.scroll.side_effect = scroll_side_effect
    engine = correlation.DNSCorrelationEngine(client, collections=[])

    existing = engine.find_existing_dns_record("WWW.Example.com.")

    assert existing == {"id": 99, "payload": {"normalized_host": "www.example.com"}}
