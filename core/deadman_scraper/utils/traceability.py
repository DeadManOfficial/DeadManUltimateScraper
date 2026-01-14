"""
NASA-Standard Traceability and Audit Logging
============================================
Logs every step of the scraping lifecycle for total accountability.
Connects to the SignalManager to capture events.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from deadman_scraper.core.signals import Signal, SignalManager

logger = logging.getLogger("AuditTrace")

class AuditLogger:
    """
    Captures signals and writes them to a NASA-grade audit trail.
    """

    def __init__(self, signals: SignalManager, audit_file: str = "nasa_audit_trail.jsonl"):
        self.signals = signals
        self.audit_path = Path(audit_file)
        self._setup_handlers()

    def _setup_handlers(self):
        """Connect handlers to relevant signals for traceability."""
        self.signals.connect_handler(Signal.ENGINE_STARTED, self._on_engine_start)
        self.signals.connect_handler(Signal.FETCH_SUCCESS, self._on_fetch_success)
        self.signals.connect_handler(Signal.FETCH_FAILED, self._on_fetch_fail)
        self.signals.connect_handler(Signal.ITEM_SCRAPED, self._on_item_scraped)
        self.signals.connect_handler(Signal.PROXY_ROTATED, self._on_proxy_rotate)

    def _log_event(self, signal: Signal, data: dict[str, Any]):
        """NASA Standard: Atomic, timestamped, immutable logging."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": signal.name,
            **data
        }
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    async def _on_engine_start(self, **kwargs):
        self._log_event(Signal.ENGINE_STARTED, {"status": "SUCCESS"})

    async def _on_fetch_success(self, url: str, layer: int, **kwargs):
        self._log_event(Signal.FETCH_SUCCESS, {"url": url, "layer": layer})

    async def _on_fetch_fail(self, url: str, error: str, **kwargs):
        self._log_event(Signal.FETCH_FAILED, {"url": url, "error": error})

    async def _on_item_scraped(self, url: str, **kwargs):
        self._log_event(Signal.ITEM_SCRAPED, {"url": url})

    async def _on_proxy_rotate(self, proxy: str, **kwargs):
        self._log_event(Signal.PROXY_ROTATED, {"proxy": proxy})
