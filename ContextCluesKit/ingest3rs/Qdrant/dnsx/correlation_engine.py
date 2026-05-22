"""Correlation helpers for linking dnsx records to existing Qdrant subdomain data."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

try:  # qdrant-client is an optional runtime dependency for this repository.
    from qdrant_client.http import models
except ImportError:  # pragma: no cover - exercised in environments without qdrant-client.
    models = None  # type: ignore[assignment]

try:
    from dns_payload_service import subdomain_dns_payload
except ImportError:  # pragma: no cover
    from .dns_payload_service import subdomain_dns_payload


def normalize_hostname(hostname: Any) -> str:
    """Return a canonical hostname for exact Qdrant payload matching."""
    return str(hostname or "").strip().lower().rstrip(".")


class DNSCorrelationEngine:
    """Correlate dnsx records with existing subdomain collections."""

    DEFAULT_COLLECTIONS = [
        "Subfinder_json",
        "subfinder",
        "subdomains_collection",
        "sublist3r",
        "amass",
        "assetfinder",
    ]
    MATCH_FIELDS = ("normalized_host", "hostname", "host", "subdomain", "domain", "name")

    def __init__(self, client: Any, collections: Optional[Sequence[str]] = None):
        self.client = client
        self.collections = list(collections or self.DEFAULT_COLLECTIONS)
        self.stats = {"matched": 0, "unmatched": 0, "updated": 0, "errors": 0}

    def _collection_names(self) -> set[str]:
        return {collection.name for collection in self.client.get_collections().collections}

    def _scroll_field_match(self, collection_name: str, field: str, value: str):
        if models is None:
            raise RuntimeError("qdrant-client is required for Qdrant correlation")
        return self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key=field, match=models.MatchValue(value=value))]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )

    def find_matching_subdomain(self, hostname: str) -> Optional[Dict[str, Any]]:
        normalized = normalize_hostname(hostname)
        if not normalized:
            return None

        available = self._collection_names()
        for collection_name in self.collections:
            if collection_name not in available:
                continue
            for field in self.MATCH_FIELDS:
                points, _ = self._scroll_field_match(collection_name, field, normalized)
                if points:
                    point = points[0]
                    return {
                        "id": point.id,
                        "payload": getattr(point, "payload", {}) or {},
                        "collection": collection_name,
                        "matched_field": field,
                    }
        return None

    def find_existing_dns_record(self, hostname: str, collection_name: str = "dnsx_records") -> Optional[Dict[str, Any]]:
        normalized = normalize_hostname(hostname)
        if not normalized:
            return None
        for field in ("normalized_host", "host"):
            points, _ = self._scroll_field_match(collection_name, field, normalized)
            if points:
                point = points[0]
                return {"id": point.id, "payload": getattr(point, "payload", {}) or {}}
        return None

    def correlate_dns_record(self, dns_record: Dict[str, Any]) -> Dict[str, Any]:
        hostname = normalize_hostname(dns_record.get("host"))
        if not hostname:
            self.stats["errors"] += 1
            dns_record["correlation_status"] = "missing_host"
            return dns_record

        dns_record["normalized_host"] = hostname
        subdomain = self.find_matching_subdomain(hostname)
        if subdomain:
            dns_record["linked_subdomain_id"] = subdomain["id"]
            dns_record["linked_collection"] = subdomain["collection"]
            dns_record["linked_match_field"] = subdomain["matched_field"]
            dns_record["correlation_status"] = "matched"
            dns_record.update(subdomain_dns_payload(dns_record))
            self.stats["matched"] += 1
        else:
            dns_record["correlation_status"] = "unmatched"
            self.stats["unmatched"] += 1
        return dns_record

    def update_subdomain_with_dns_info(self, dns_record: Dict[str, Any]) -> bool:
        if dns_record.get("correlation_status") != "matched":
            return False
        subdomain_id = dns_record.get("linked_subdomain_id")
        collection = dns_record.get("linked_collection")
        if subdomain_id is None or not collection:
            return False

        payload: Dict[str, Any] = {
            "latest_dns_record_id": dns_record.get("id"),
            "latest_dns_timestamp": dns_record.get("timestamp"),
            "dns_correlation_status": "active",
        }
        payload.update(subdomain_dns_payload(dns_record))

        try:
            self.client.set_payload(collection_name=collection, points=[subdomain_id], payload=payload)
        except Exception as exc:
            print(f"⚠️ Failed to update linked subdomain {subdomain_id}: {exc}")
            return False
        self.stats["updated"] += 1
        return True

    def prepare_upsert_operation(self, dns_record: Dict[str, Any], collection_name: str = "dnsx_records") -> Dict[str, Any]:
        existing = self.find_existing_dns_record(str(dns_record.get("normalized_host") or dns_record.get("host") or ""), collection_name)
        if existing:
            return {"operation": "update", "point_id": existing["id"], "record": dns_record}
        return {"operation": "insert", "point_id": None, "record": dns_record}

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()

    def reset_stats(self) -> None:
        self.stats = {"matched": 0, "unmatched": 0, "updated": 0, "errors": 0}
