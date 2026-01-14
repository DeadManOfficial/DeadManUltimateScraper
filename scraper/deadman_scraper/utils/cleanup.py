"""
NASA-Standard Cleanup and Organization Utility
==============================================
Maintains project integrity by moving artifacts to designated storage.
Purges temporary folders and legacy files.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger("Cleanup")

class ProjectPurge:
    """
    Orchestrates the organization of the project root.
    """

    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.data_dir = self.root / "data"
        self.log_dir = self.root / "logs"
        self.tmp_dir = self.root / "tmp"

        # Ensure target dirs exist
        for d in [self.data_dir, self.log_dir, self.tmp_dir]:
            d.mkdir(exist_ok=True)

    def execute(self):
        """Perform the purge and organization."""
        logger.info("Starting NASA-standard project purge...")

        # 1. Move Logs
        for log in self.root.glob("*.log*"):
            if log.name != "central_scraper.log": # Keep main log for now
                shutil.move(str(log), self.log_dir / log.name)

        # 2. Move Data/Scrapes
        for txt in self.root.glob("scraped_page_*.txt"):
            shutil.move(str(txt), self.data_dir / txt.name)

        if (self.root / "scraper_discovery.json").exists():
            shutil.move(str(self.root / "scraper_discovery.json"), self.data_dir / "scraper_discovery.json")

        # 3. Purge Temporary Folders
        for tmp_folder in self.root.glob("tmpclaude-*"):
            if tmp_folder.is_dir():
                try:
                    shutil.rmtree(tmp_folder)
                except Exception as e:
                    logger.warning(f"Could not delete {tmp_folder}: {e}")

        # 4. Handle Local DBs
        for db in self.root.glob("*.db"):
            shutil.move(str(db), self.data_dir / db.name)

        logger.info("Purge complete. Project root is now NASA-standard clean.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    purge = ProjectPurge(Path("G:/DeadManUltimateScraper"))
    purge.execute()
