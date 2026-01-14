"""
Stealth JavaScript Injection
============================
Injects anti-detection JavaScript into browser sessions.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StealthInjector:
    """
    Injects comprehensive anti-detection JavaScript into browsers.

    Bypasses:
    - WebDriver detection
    - Chrome runtime checks
    - Canvas fingerprinting
    - WebGL fingerprinting
    - Plugin enumeration
    - Battery API
    - Media devices enumeration
    - Headless detection
    """

    # Main stealth script
    STEALTH_SCRIPT = """
    // === WEBDRIVER DETECTION BYPASS ===
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // === CHROME RUNTIME SPOOFING ===
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };

    // === PERMISSIONS API ===
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // === PLUGIN SPOOFING ===
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {
                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                description: "Portable Document Format",
                filename: "internal-pdf-viewer",
                length: 1,
                name: "Chrome PDF Plugin"
            },
            {
                0: {type: "application/pdf", suffixes: "pdf", description: ""},
                description: "",
                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                length: 1,
                name: "Chrome PDF Viewer"
            },
            {
                0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                description: "",
                filename: "internal-nacl-plugin",
                length: 2,
                name: "Native Client"
            }
        ]
    });

    // === LANGUAGES ===
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });

    // === CANVAS FINGERPRINT RANDOMIZATION ===
    const getImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function() {
        const imageData = getImageData.apply(this, arguments);
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] += Math.random() * 0.1 - 0.05;
        }
        return imageData;
    };

    // === WEBGL FINGERPRINT SPOOFING ===
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.apply(this, arguments);
    };

    // === BATTERY API ===
    Object.defineProperty(navigator, 'getBattery', {
        get: () => undefined
    });

    // === MEDIA DEVICES ===
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        navigator.mediaDevices.enumerateDevices = () => Promise.resolve([
            {deviceId: "default", kind: "audioinput", label: "", groupId: ""},
            {deviceId: "default", kind: "audiooutput", label: "", groupId: ""},
            {deviceId: "default", kind: "videoinput", label: "", groupId: ""}
        ]);
    }

    // === AUTOMATION DETECTION ===
    window.document.documentElement.setAttribute('webdriver', 'false');

    // === HEADLESS DETECTION BYPASS ===
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => 1
    });

    // === CONNECTION API ===
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false
        })
    });

    // === HARDWARE CONCURRENCY ===
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });

    // === DEVICE MEMORY ===
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });

    console.log('[STEALTH] Anti-detection JavaScript injected');
    """

    # Additional script for WebGL2
    WEBGL2_SCRIPT = """
    // === WEBGL2 FINGERPRINT SPOOFING ===
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter2.apply(this, arguments);
        };
    }
    """

    # Audio context spoofing
    AUDIO_SCRIPT = """
    // === AUDIO CONTEXT FINGERPRINT ===
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
        const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
        AudioContext.prototype.createAnalyser = function() {
            const analyser = originalCreateAnalyser.apply(this, arguments);
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
            analyser.getFloatFrequencyData = function(array) {
                originalGetFloatFrequencyData.apply(this, arguments);
                for (let i = 0; i < array.length; i++) {
                    array[i] += Math.random() * 0.0001;
                }
            };
            return analyser;
        };
    }
    """

    @classmethod
    def get_full_script(cls) -> str:
        """Get complete stealth script with all components."""
        return cls.STEALTH_SCRIPT + cls.WEBGL2_SCRIPT + cls.AUDIO_SCRIPT

    @classmethod
    def inject_selenium(cls, driver: Any) -> bool:
        """
        Inject stealth script into Selenium WebDriver.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if injection successful
        """
        if not driver:
            return False

        try:
            # Use CDP for Chrome/Edge
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": cls.get_full_script()},
            )
            logger.debug("[STEALTH] Injected via CDP")
            return True
        except Exception:
            # Fallback: execute directly
            try:
                driver.execute_script(cls.get_full_script())
                logger.debug("[STEALTH] Injected via execute_script")
                return True
            except Exception as e:
                logger.error(f"[STEALTH] Injection failed: {e}")
                return False

    @classmethod
    async def inject_playwright(cls, page: Any) -> bool:
        """
        Inject stealth script into Playwright page.

        Args:
            page: Playwright Page instance

        Returns:
            True if injection successful
        """
        if not page:
            return False

        try:
            await page.add_init_script(cls.get_full_script())
            logger.debug("[STEALTH] Injected into Playwright page")
            return True
        except Exception as e:
            logger.error(f"[STEALTH] Playwright injection failed: {e}")
            return False

    @classmethod
    async def inject_nodriver(cls, tab: Any) -> bool:
        """
        Inject stealth script into nodriver tab.

        Args:
            tab: nodriver Tab instance

        Returns:
            True if injection successful
        """
        if not tab:
            return False

        try:
            await tab.evaluate(cls.get_full_script())
            logger.debug("[STEALTH] Injected into nodriver tab")
            return True
        except Exception as e:
            logger.error(f"[STEALTH] nodriver injection failed: {e}")
            return False
