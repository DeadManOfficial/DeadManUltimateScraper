"""
NASA-Standard API Quota Tracker
===============================
Parses and updates secrets file to track "Free Forever" usage.
Ensures total accountability and quota compliance.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("QuotaTracker")

MASTER_FILE = Path(os.getenv("SECRETS_FILE", Path.home() / ".secrets" / "DEADMAN_API_MASTER.md"))

class QuotaTracker:
    """
    Manages the reading and updating of API usage in the master secrets file.
    """

    @staticmethod
    def get_current_usage(api_name: str) -> dict[str, str]:
        """
        Extract usage stats for a specific API from the markdown table.
        """
        if not MASTER_FILE.exists():
            return {}

        content = MASTER_FILE.read_text(encoding="utf-8")
        # Match table row for API
        pattern = rf"\| {api_name} \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            return {
                "used": match.group(1).strip(),
                "remaining": match.group(2).strip(),
                "limit": match.group(3).strip(),
                "period": match.group(4).strip()
            }
        return {}

    @staticmethod
    def update_usage(api_name: str, used_increment: int, remaining_new: str, log_message: str):
        """
        NASA Standard: Atomic update of the master usage tracker.
        Updates the table, the detailed usage section, and adds a log entry.
        """
        if not MASTER_FILE.exists():
            logger.error(f"Master file not found at {MASTER_FILE}")
            return

        content = MASTER_FILE.read_text(encoding="utf-8")

        # 1. Update the USAGE TRACKER table
        # Extract current 'Used' value to increment it
        table_pattern = rf"(\| {api_name} \| )(.*?) (\| )(.*?) (\|)"
        table_match = re.search(table_pattern, content, re.IGNORECASE)

        if table_match:
            current_used_str = table_match.group(2).strip()
            # Handle units like 'tkn' or 'req'
            num_match = re.search(r"(\d+)", current_used_str)
            if num_match:
                new_used_val = int(num_match.group(1)) + used_increment
                unit = current_used_str.replace(num_match.group(1), "").strip()
                new_used_str = f"{new_used_val} {unit}".strip()

                # Replace in table
                new_row = f"{table_match.group(1)}{new_used_str:<7} {table_match.group(3)}{remaining_new:<9} {table_match.group(5)}"
                content = content.replace(table_match.group(0), new_row)

        # 2. Update the CREDENTIALS + DETAILED TRACKING section
        detail_pattern = rf"(## {api_name.upper()}.*?Used:\s+)(.*?)(\n.*?Remaining:\s+)(.*?)(\n)"
        detail_match = re.search(detail_pattern, content, re.DOTALL | re.IGNORECASE)

        if detail_match:
            # Similar logic for detail section
            current_detail_used = detail_match.group(2).strip()
            num_match_detail = re.search(r"(\d+)", current_detail_used)
            if num_match_detail:
                new_used_detail = int(num_match_detail.group(1)) + used_increment
                unit_detail = current_detail_used.replace(num_match_detail.group(1), "").strip()
                new_used_detail_str = f"{new_used_detail} {unit_detail}".strip()

                content = content.replace(
                    detail_match.group(0),
                    f"{detail_match.group(1)}{new_used_detail_str}{detail_match.group(3)}{remaining_new}{detail_match.group(5)}"
                )

        # 3. Add to the Log section
        log_header_pattern = rf"(## {api_name.upper()}.*?\*\*Log:\*\*\n)"
        log_match = re.search(log_header_pattern, content, re.DOTALL | re.IGNORECASE)

        if log_match:
            date_str = datetime.now().strftime("%Y-%m-%d")
            new_log_entry = f"- {date_str}: {log_message}\n"
            content = content.replace(log_match.group(1), f"{log_match.group(1)}{new_log_entry}")

        # 4. Update "Last Updated" timestamp
        content = re.sub(
            r"\*\*Last Updated:\*\*.*",
            f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
            content
        )

        # Write back atomically
        MASTER_FILE.write_text(content, encoding="utf-8")
        logger.info(f"Updated {api_name} quota: +{used_increment} used.")
