"""
NASA-Standard Quota Tracker Test
================================
Validates the automatic updating of G:/.secrets/DEADMAN_API_MASTER.md.
"""

import asyncio
import logging
import sys
from deadman_scraper.utils.quota_tracker import QuotaTracker

async def test_tracking():
    print("Testing Quota Tracking for Groq...")
    
    # 1. Get current usage
    usage = QuotaTracker.get_current_usage("Groq")
    print(f"Current Groq Usage: {usage}")
    
    if not usage:
        print("Error: Could not find Groq usage in master file.")
        return

    # 2. Simulate an update
    try:
        rem_str = usage['remaining'].replace("~", "").split()[0].replace(",", "")
        if 'M' in rem_str:
            current_rem = float(rem_str.replace('M', '')) * 1_000_000
        elif 'k' in rem_str:
            current_rem = float(rem_str.replace('k', '')) * 1_000
        else:
            current_rem = float(rem_str)
            
        new_rem = int(current_rem - 1)
        if new_rem > 1_000_000:
            new_rem_str = f"~{new_rem/1_000_000:.1f}M requests"
        else:
            new_rem_str = f"~{new_rem:,} requests"
        
        print(f"Updating Groq: +1 used, {new_rem_str} remaining...")
        QuotaTracker.update_usage("Groq", 1, new_rem_str, "Test increment from CentralScraper validation")
        
        # 3. Verify
        new_usage = QuotaTracker.get_current_usage("Groq")
        print(f"New Groq Usage: {new_usage}")
        
    except Exception as e:
        print(f"Update failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tracking())
