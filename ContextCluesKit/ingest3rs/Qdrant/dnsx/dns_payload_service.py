"""Reusable dnsx payload mechanics for correlation updates."""

from __future__ import annotations

from typing import Any, Dict

DNS_TO_SUBDOMAIN_PAYLOAD_FIELDS = {
    "a": "resolved_ips",
    "aaaa": "resolved_ipv6",
    "cname": "cname",
}


def subdomain_dns_payload(dns_record: Dict[str, Any]) -> Dict[str, Any]:
    """Return DNS fields that should be copied onto linked subdomain payloads."""
    return {
        target_field: dns_record[source_field]
        for source_field, target_field in DNS_TO_SUBDOMAIN_PAYLOAD_FIELDS.items()
        if dns_record.get(source_field)
    }
