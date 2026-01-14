"""
Stealth Suite
=============
Anti-detection and human simulation for evading bot protection.
"""

from deadman_scraper.stealth.behavior import BehavioralSimulator
from deadman_scraper.stealth.fingerprint import FingerprintSpoofer
from deadman_scraper.stealth.headers import HeaderGenerator
from deadman_scraper.stealth.injector import StealthInjector
from deadman_scraper.stealth.session import SessionStealer

__all__ = [
    "StealthInjector",
    "BehavioralSimulator",
    "FingerprintSpoofer",
    "HeaderGenerator",
    "SessionStealer",
]
