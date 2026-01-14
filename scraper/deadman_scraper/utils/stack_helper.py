"""
NASA-Standard Graphite Stack Helper
===================================
Automates the verification and submission of Graphite stacks.
Ensures every increment meets quality gates before hitting GitHub.
"""

import subprocess
import logging
import sys
from pathlib import Path

from .static_analysis import QualityChecker

logger = logging.getLogger("StackHelper")

class MissionStacker:
    """
    Orchestrates high-fidelity code stacking using Graphite.
    """

    @staticmethod
    def verify_and_submit():
        """
        NASA Standard: Verify quality gates then submit stack.
        """
        logger.info("Initiating Pre-Submission Quality Gate...")
        
        project_root = Path(__file__).parent.parent.parent
        
        # 1. Static Analysis
        QualityChecker.run_all(project_root)
        
        # 2. Unit Tests
        logger.info("Running Unit Test Suite...")
        test_result = subprocess.run(["pytest", "tests/unit"], cwd=str(project_root))
        
        if test_result.returncode != 0:
            logger.error("Quality gate FAILED. Fix errors before stacking.")
            return False

        # 3. Graphite Submission
        logger.info("Quality gate PASSED. Submitting stack to Command Center...")
        try:
            subprocess.run(["gt", "submit", "--no-edit"], check=True)
            logger.info("Stack successfully submitted.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Graphite submission failed: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MissionStacker.verify_and_submit()
