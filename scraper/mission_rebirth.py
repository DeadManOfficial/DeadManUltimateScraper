"""
MISSION: REBIRTH
================
NASA-Standard Intelligence Mission.
Re-targeting original failures with the "God Module" stack.
"""

import asyncio
import json
from central_scraper import CentralScraper, ScrapeRequest
from deadman_scraper.core.mission import AutonomousMission, MissionParams

async def main():
    print("\n" + "═"*60)
    print("🚀 INITIATING MISSION: REBIRTH")
    print("═"*60 + "\n")

    async with CentralScraper() as god:
        # 1. Re-target original Reddit failures
        print("[*] PHASE 1: Re-targeting original blocks...")
        original_targets = [
            "https://www.reddit.com/r/WebScrapingTools/",
            "https://www.reddit.com/r/webscraping/comments/1bpk4l2/what_are_the_best_tools_out_there/",
            "https://www.reddit.com/r/webscraping/comments/zg93ht/what_is_the_best_free_web_scraping_tool/"
        ]
        
        for url in original_targets:
            req = ScrapeRequest(url=url, use_tor=True, use_llm=False)
            result = await god.scrape(req)
            status = "SUCCESS" if result.success else "FAILED"
            layer = f" (Layer: {result.fetch_layer})" if result.success else ""
            print(f"  [{status}]{layer} {url}")
            if not result.success:
                print(f"    Reason: {result.error}")

        # 2. "And then some" - Autonomous Intelligence Burst
        print("\n[*] PHASE 2: Initiating Intelligence Burst (Clearnet + Darknet)...")
        mission = AutonomousMission(god)
        params = MissionParams(
            focus_areas=[
                "SynthID watermark bypass github",
                "Cloudflare Datadome bypass techniques 2026",
                "DeepMind watermark crack .onion"
            ],
            burst_intensity=8,
            use_tor=True
        )
        
        findings = await mission.execute_burst(params)
        
        # 3. Final Intelligence Synthesis
        if findings:
            print("\n" + "═"*60)
            print("🧠 FINAL INTELLIGENCE SYNTHESIS")
            print("═"*60)
            analysis_prompt = f"Analyze these {len(findings)} findings for actionable bypass techniques: {findings}"
            summary = await god.gather_intel_analysis(analysis_prompt)
            print(f"\n{summary}\n")
        else:
            print("\n[!] No new intelligence markers identified in this burst.")

if __name__ == "__main__":
    asyncio.run(main())
