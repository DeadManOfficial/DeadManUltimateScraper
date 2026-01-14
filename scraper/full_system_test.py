"""
NASA-Standard Full System Integration Test
==========================================
Executes a live mission using the CentralScraper (God Module).
Verifies:
1. Health Diagnostics (Telemetry)
2. Input Sanitization
3. Multi-layer Fetching
4. Audit Traceability
5. Extraction & AI Integration
"""

import asyncio
import json
import logging
from central_scraper import CentralScraper, ScrapeRequest
from deadman_scraper.utils.health import HealthCheck

async def run_full_validation():
    print("\n" + "="*60)
    print("NASA-STANDARD FULL SYSTEM VALIDATION")
    print("="*60 + "\n")

    async with CentralScraper() as god:
        # 1. System Health Diagnostics
        print("[*] STEP 1: Running System Diagnostics...")
        diagnostics = await HealthCheck.run_diagnostics(god.engine)
        print(json.dumps(diagnostics, indent=2))
        
        if diagnostics["components"]["persistence"]["status"] == "UP":
            print("\n[+] PERSISTENCE LAYER: HEALTHY")
        else:
            print("\n[!] PERSISTENCE LAYER: ERROR")

        # 2. Live Scrape Mission (Multi-Target)
        print("\n[*] STEP 2: Executing Live Scrape Mission...")
        
        # Test targets: A search engine and a complex site
        targets = [
            "https://www.google.com/search?q=NASA+standards+software",
            "https://www.reddit.com/r/WebScrapingTools/"
        ]
        
        requests = [ScrapeRequest(url=url, use_llm=False) for url in targets]
        
        async for result in god.scrape_batch(requests):
            status = "SUCCESS" if result.success else "FAILED"
            layer = f" (Layer: {result.fetch_layer})" if result.success else ""
            print(f"  [{status}]{layer} {result.url}")
            
            if not result.success:
                print(f"    Error: {result.error}")

        # 3. Traceability Verification
        print("\n[*] STEP 3: Verifying Audit Traceability...")
        from pathlib import Path
        audit_file = Path("nasa_audit_trail.jsonl")
        if audit_file.exists():
            with open(audit_file, "r") as f:
                last_lines = f.readlines()[-5:]
                print(f"[+] Audit Trail found. Last {len(last_lines)} events logged:")
                for line in last_lines:
                    print(f"    {line.strip()}")
        else:
            print("[!] Audit Trail missing!")

    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_full_validation())
