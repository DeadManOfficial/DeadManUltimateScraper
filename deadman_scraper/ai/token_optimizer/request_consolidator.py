# [TRACEABILITY] REQ-301
from collections import defaultdict
from typing import Optional

class RequestConsolidator:
    """
    Consolidates multiple requests into single API call
    Target: 50-70% token savings through batching
    """

    def __init__(self):
        self.pending_requests = defaultdict(list)

    def add_request(self, category: str, request: str):
        """Add request to batch"""
        self.pending_requests[category].append(request)

    def get_consolidated_prompt(self, category: str) -> Optional[str]:
        """Get consolidated prompt for category"""
        requests = self.pending_requests.get(category, [])

        if not requests:
            return None

        if len(requests) == 1:
            return requests[0]

        consolidated = f"Complete {len(requests)} tasks:\n\n"
        for i, req in enumerate(requests, 1):
            consolidated += f"{i}. {req}\n"

        self.pending_requests[category] = []
        return consolidated
