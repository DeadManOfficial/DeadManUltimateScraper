"""
NASA-Standard Unit Tests: FingerprintSpoofer
============================================
Tests for JA3/JA4 generation and browser fingerprint consistency.
"""

import pytest
from deadman_scraper.stealth.fingerprint import FingerprintSpoofer, BrowserFingerprint

def test_fingerprint_generation():
    """Verify consistent fingerprint generation."""
    fp = FingerprintSpoofer.generate_fingerprint(browser="chrome", version="120")
    assert "Chrome/120" in fp.user_agent
    assert fp.platform == "Win32"
    assert fp.screen_width in [w for w, h in FingerprintSpoofer.SCREEN_RESOLUTIONS]

def test_ja4_generation():
    """Verify JA4 TLS fingerprint format."""
    ja4 = FingerprintSpoofer.generate_ja4(browser="chrome")
    assert ja4.startswith("t13d1516h2_")
    assert len(ja4.split("_")) == 3

def test_fingerprint_js_injection():
    """Verify generated JS contains expected properties."""
    fp = FingerprintSpoofer.generate_fingerprint()
    js = FingerprintSpoofer.get_fingerprint_js(fp)
    assert str(fp.screen_width) in js
    assert fp.webgl_vendor in js
    assert "Object.defineProperty" in js

def test_canvas_noise_js():
    """Verify canvas noise JS generation."""
    js = FingerprintSpoofer.generate_canvas_noise_js()
    assert "HTMLCanvasElement.prototype.toDataURL" in js
    assert "Math.random()" in js
