"""
Correlation Engine for dnsx Data Integration

Handles automatic correlation between dnsx DNS records and existing subdomain
collections in Qdrant. Provides bidirectional linking and latest-only updates.
"""

from typing import Dict, List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models


class DNSCorrelationEngine:
    """
    Engine for correlating dnsx DNS records with existing subdomain collections.

    Features:
    - Automatic subdomain matching by hostname
    - Bidirectional linking (DNS record ↔ Subdomain)
    - Latest-only tracking (upsert mode)
    - Support for multiple subdomain collections
    """

    # Common subdomain collection names to search
    DEFAULT_COLLECTIONS = ["subdomains_collection", "subfinder", "sublist3r", "amass"]

    def __init__(self, client: QdrantClient, collections: List[str] = None):
        """
        Initialize correlation engine.

        Args:
            client: QdrantClient instance
            collections: List of collection names to search for subdomains.
                        Defaults to DEFAULT_COLLECTIONS.
        """
        self.client = client
        self.collections = collections or self.DEFAULT_COLLECTIONS
        self.stats = {"matched": 0, "unmatched": 0, "updated": 0, "errors": 0}

    def find_matching_subdomain(self, hostname: str) -> Optional[Dict[str, Any]]:
        """
        Search for a matching subdomain across all configured collections.

        Args:
            hostname: The hostname to search for (e.g., "www.example.com")

        Returns:
            Dictionary with subdomain data and collection info, or None if not found.
            Format: {"id": point_id, "payload": payload, "collection": collection_name}
        """
        for collection_name in self.collections:
            try:
                # Check if collection exists
                collections = [
                    c.name for c in self.client.get_collections().collections
                ]
                if collection_name not in collections:
                    continue

                # Search for matching hostname
                results = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="hostname", match=models.MatchValue(value=hostname)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )

                if results[0]:
                    point = results[0][0]
                    return {
                        "id": point.id,
                        "payload": point.payload,
                        "collection": collection_name,
                        "vector_id": point.id,
                    }

            except Exception as e:
                print(f"[WARNING] Error searching collection {collection_name}: {e}")
                continue

        return None

    def find_existing_dns_record(
        self, hostname: str, collection_name: str = "dnsx_records"
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a DNS record for this hostname already exists (for upsert).

        Args:
            hostname: The hostname to check
            collection_name: DNS collection name to search

        Returns:
            Dictionary with existing record info, or None if not found.
        """
        try:
            results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="host", match=models.MatchValue(value=hostname)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            if results[0]:
                point = results[0][0]
                return {"id": point.id, "payload": point.payload}

        except Exception as e:
            print(f"[WARNING] Error checking for existing DNS record: {e}")

        return None

    def correlate_dns_record(self, dns_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Correlate a single DNS record with existing subdomains.

        Args:
            dns_record: The DNS record from convert_dnsxJSON.py

        Returns:
            Enriched DNS record with correlation fields.
        """
        hostname = dns_record.get("host", "")
        if not hostname:
            self.stats["errors"] += 1
            return dns_record

        # Search for matching subdomain
        subdomain = self.find_matching_subdomain(hostname)

        if subdomain:
            # Add correlation fields
            dns_record["linked_subdomain_id"] = subdomain["id"]
            dns_record["linked_collection"] = subdomain["collection"]
            dns_record["correlation_status"] = "matched"

            # Add resolved_ips for quick reference
            if dns_record.get("a"):
                dns_record["resolved_ips"] = dns_record["a"]

            self.stats["matched"] += 1
            print(
                f"[CORRELATION] Matched '{hostname}' to {subdomain['collection']} ID {subdomain['id']}"
            )
        else:
            dns_record["correlation_status"] = "unmatched"
            self.stats["unmatched"] += 1
            print(f"[CORRELATION] No match found for '{hostname}'")

        return dns_record

    def update_subdomain_with_dns_info(self, dns_record: Dict[str, Any]) -> bool:
        """
        Update the linked subdomain record with latest DNS information.

        Args:
            dns_record: The correlated DNS record

        Returns:
            True if update successful, False otherwise.
        """
        if dns_record.get("correlation_status") != "matched":
            return False

        subdomain_id = dns_record.get("linked_subdomain_id")
        collection = dns_record.get("linked_collection")

        if not subdomain_id or not collection:
            return False

        try:
            # Prepare update payload
            update_payload = {
                "latest_dns_record_id": dns_record.get("id"),
                "latest_dns_timestamp": dns_record.get("timestamp"),
                "dns_correlation_status": "active",
            }

            # Add resolved IPs if available
            if dns_record.get("a"):
                update_payload["resolved_ips"] = dns_record["a"]

            if dns_record.get("aaaa"):
                update_payload["resolved_ipv6"] = dns_record["aaaa"]

            # Update the subdomain record
            self.client.set_payload(
                collection_name=collection,
                points=[subdomain_id],
                payload=update_payload,
            )

            self.stats["updated"] += 1
            print(f"[UPDATE] Updated subdomain ID {subdomain_id} with DNS info")
            return True

        except Exception as e:
            print(f"[WARNING] Failed to update subdomain {subdomain_id}: {e}")
            return False

    def prepare_upsert_operation(
        self, dns_record: Dict[str, Any], collection_name: str = "dnsx_records"
    ) -> Dict[str, Any]:
        """
        Prepare DNS record for upsert operation (latest-only tracking).

        Args:
            dns_record: The DNS record to prepare
            collection_name: Target collection name

        Returns:
            Dictionary with operation type and point data.
            Format: {"operation": "insert"|"update", "point_id": id|None, "record": record}
        """
        hostname = dns_record.get("host", "")

        # Check for existing record
        existing = self.find_existing_dns_record(hostname, collection_name)

        if existing:
            # Update existing record
            return {
                "operation": "update",
                "point_id": existing["id"],
                "record": dns_record,
            }
        else:
            # Insert new record - generate new ID
            return {"operation": "insert", "point_id": None, "record": dns_record}

    def get_stats(self) -> Dict[str, int]:
        """Get correlation statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset correlation statistics."""
        self.stats = {"matched": 0, "unmatched": 0, "updated": 0, "errors": 0}
