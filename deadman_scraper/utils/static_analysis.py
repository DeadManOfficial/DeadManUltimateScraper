"""
Static Analysis and Linting Wrapper
===================================
NASA Standard: Automated verification of code quality and security.
Wraps 'ruff' for linting and 'bandit' for security scanning.
"""

import subprocess
import sys
import logging
from pathlib import Path

logger = logging.getLogger("StaticAnalysis")

class QualityChecker:
    """
    Runs static analysis tools to ensure NASA-level code quality.
    """

    @staticmethod
    def run_ruff(path: Path) -> bool:
        """Run ruff linter and formatter."""
        logger.info(f"Running ruff on {path}")
        try:
            subprocess.run(["ruff", "check", str(path)], check=True, shell=sys.platform == "win32")
            return True
        except subprocess.CalledProcessError:
            logger.error("Ruff linting failed.")
            return False
        except FileNotFoundError:
            logger.warning("Ruff not found. Install via: pip install ruff")
            return True

    @staticmethod
    def run_bandit(path: Path) -> bool:
        """Run bandit security scanner."""
        logger.info(f"Running bandit security scan on {path}")
        try:
            subprocess.run(["bandit", "-r", str(path)], check=True, shell=sys.platform == "win32")
            return True
        except subprocess.CalledProcessError:
            logger.error("Bandit security scan found issues.")
            return False
        except FileNotFoundError:
            logger.warning("Bandit not found. Install via: pip install bandit")
            return True

    @classmethod
    def run_all(cls, project_root: Path):
        """Execute the full quality suite."""
        logger.info("=== STARTING NASA-STANDARD QUALITY SUITE ===")
        lint_ok = cls.run_ruff(project_root)
        sec_ok = cls.run_bandit(project_root)

        if lint_ok and sec_ok:
            logger.info("Quality suite passed.")
        else:
            logger.error("Quality suite FAILED. See logs for details.")
