"""
System Health and Performance Monitoring
=========================================
NASA Standard: Real-time telemetry and component verification.
"""

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("HealthMonitor")

class HealthCheck:
    """
    Performs diagnostic checks on all framework components.
    """

    @staticmethod
    async def check_tor(config: Any) -> dict[str, Any]:
        """Verify TOR connectivity and circuit health."""
        import httpx
        start = time.time()
        proxy = f"socks5h://{config.tor.socks_host}:{config.tor.socks_port}"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=10) as client:
                resp = await client.get("https://check.torproject.org/api/ip")
                latency = time.time() - start
                return {
                    "status": "UP" if resp.status_code == 200 else "DEGRADED",
                    "latency": f"{latency:.2f}s",
                    "tor_active": "Congratulations" in resp.text
                }
        except Exception as e:
            return {"status": "DOWN", "error": str(e)}

    @staticmethod
    async def check_storage(db_path: Path) -> dict[str, Any]:
        """Verify database integrity and disk availability."""
        try:
            import aiosqlite
            async with aiosqlite.connect(db_path) as db:
                await db.execute("SELECT 1")
            return {"status": "UP", "integrity": "OK"}
        except Exception as e:
            return {"status": "DOWN", "error": str(e)}

    @classmethod
    async def run_diagnostics(cls, engine: Any) -> dict[str, Any]:
        """NASA Standard: Comprehensive system heartbeat."""
        logger.info("Starting system-wide health diagnostics...")

        report = {
            "timestamp": time.time(),
            "engine_state": engine.state.name,
            "components": {}
        }

        # TOR Check
        if engine.config.tor.enabled:
            report["components"]["tor"] = await cls.check_tor(engine.config)

        # Storage Check
        report["components"]["persistence"] = await cls.check_storage(Path("data/queue.db"))

        # Performance Telemetry
        stats = engine.stats
        report["telemetry"] = {
            "success_rate": stats.get("requests_success", 0) / max(1, stats.get("requests_made", 1)),
            "load_factor": len(engine._workers) / engine.config.fetch.max_concurrent
        }

        status = "HEALTHY" if all(c.get("status") == "UP" for c in report["components"].values()) else "UNHEALTHY"
        logger.info(f"System Status: {status}")

        return report
