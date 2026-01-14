"""
DEADMAN ARMORY - Mission Readiness Dashboard
============================================
NASA Standard: Integrated system telemetry and deployment automation.
Orchestrates: Cleanup -> Diagnostics -> Quality -> Graphite Stacking.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add core to path
sys.path.append(str(Path(__file__).parent / "core"))

from deadman_scraper.utils.health import HealthCheck
from deadman_scraper.utils.cleanup import ProjectPurge
from deadman_scraper.utils.static_analysis import QualityChecker
from deadman_scraper.utils.stack_helper import MissionStacker
from central_scraper import CentralScraper

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Armory")

class ArmoryControl:
    """
    Automated Control Center for the God Module ecosystem.
    """

    @staticmethod
    async def check_readiness():
        """
        Full spectrum readiness audit.
        """
        print("\n" + "█" * 60)
        print("🚀 DEADMAN ARMORY: MISSION READINESS AUDIT")
        print("█" * 60 + "\n")

        # 1. The Purge (Organization)
        print("[*] 1. Executing Project Purge...")
        purge = ProjectPurge(Path("G:/DeadManUltimateScraper"))
        purge.execute()
        print("    [OK] Root directory sanitized.\n")

        async with CentralScraper() as god:
            # 2. Health Heartbeat
            print("[*] 2. Running System Diagnostics...")
            report = await HealthCheck.run_diagnostics(god.engine)
            for comp, status in report["components"].items():
                icon = "✅" if status.get("status") == "UP" else "❌"
                print(f"    {icon} {comp.upper()}: {status.get('status')}")
            print()

            # 3. Quality Gate
            print("[*] 3. Running Static Analysis & Security Scan...")
            QualityChecker.run_all(Path("G:/DeadManUltimateScraper/scraper"))
            print()

        print("█" * 60)
        print("AUDIT COMPLETE: SYSTEM IS MISSION READY")
        print("█" * 60 + "\n")

    @staticmethod
    def deploy_stack():
        """
        Verifies and automatically pushes the latest code to Graphite.
        """
        print("\n[!] INITIATING AUTOMATED DEPLOYMENT SEQUENCE...")
        success = MissionStacker.verify_and_submit()
        if success:
            print("\n✅ DEPLOYMENT SUCCESSFUL: Stack pushed to Command Center.")
        else:
            print("\n❌ DEPLOYMENT ABORTED: Quality gate failed.")

if __name__ == "__main__":
    import sys
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if command == "status":
        asyncio.run(ArmoryControl.check_readiness())
    elif command == "deploy":
        ArmoryControl.deploy_stack()
    else:
        print("Usage: python armory.py [status|deploy]")
