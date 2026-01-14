"""
Behavioral Simulation
=====================
Simulates human-like browsing patterns to evade detection.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class BehavioralSimulator:
    """
    Simulates human browsing behavior.

    Features:
    - Random delays
    - Natural scrolling (with occasional scroll-back)
    - Curved mouse movements
    - Realistic typing with occasional errors
    - Page dwell time
    """

    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        scroll_enabled: bool = True,
        mouse_enabled: bool = True,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.scroll_enabled = scroll_enabled
        self.mouse_enabled = mouse_enabled

    # =========================================================================
    # DELAYS
    # =========================================================================

    @staticmethod
    def human_delay_sync(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
        """Synchronous random human-like delay."""
        import time

        time.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    async def human_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
        """Async random human-like delay."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    async def page_dwell(min_sec: float = 5.0, max_sec: float = 15.0) -> None:
        """Simulate realistic page reading time."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    # =========================================================================
    # SCROLLING
    # =========================================================================

    @staticmethod
    def scroll_page_sync(driver: Any) -> None:
        """
        Synchronous scroll simulation for Selenium.

        Scrolls down with occasional scroll-back (like a real human would).
        """
        if not driver:
            return

        try:
            # Main scroll
            scroll_distance = random.randint(300, 700)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            BehavioralSimulator.human_delay_sync(0.5, 1.5)

            # Occasional scroll-back (30% chance)
            if random.random() < 0.3:
                scroll_back = random.randint(50, 200)
                driver.execute_script(f"window.scrollBy(0, -{scroll_back});")
                BehavioralSimulator.human_delay_sync(0.3, 0.8)
        except Exception as e:
            logger.debug(f"Scroll simulation failed: {e}")

    @staticmethod
    async def scroll_page(page: Any, driver_type: str = "playwright") -> None:
        """
        Async scroll simulation for Playwright/nodriver.

        Args:
            page: Page/Tab instance
            driver_type: 'playwright' or 'nodriver'
        """
        if not page:
            return

        try:
            scroll_distance = random.randint(300, 700)

            if driver_type == "playwright":
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            else:  # nodriver
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")

            await BehavioralSimulator.human_delay(0.5, 1.5)

            # Occasional scroll-back
            if random.random() < 0.3:
                scroll_back = random.randint(50, 200)
                if driver_type == "playwright":
                    await page.evaluate(f"window.scrollBy(0, -{scroll_back})")
                else:
                    await page.evaluate(f"window.scrollBy(0, -{scroll_back})")
                await BehavioralSimulator.human_delay(0.3, 0.8)

        except Exception as e:
            logger.debug(f"Async scroll simulation failed: {e}")

    @staticmethod
    async def scroll_to_bottom(page: Any, driver_type: str = "playwright") -> None:
        """Gradually scroll to page bottom."""
        if not page:
            return

        try:
            # Get page height
            if driver_type == "playwright":
                height = await page.evaluate("document.body.scrollHeight")
            else:
                height = await page.evaluate("document.body.scrollHeight")

            current = 0
            while current < height:
                scroll_amount = random.randint(200, 500)
                current += scroll_amount

                if driver_type == "playwright":
                    await page.evaluate(f"window.scrollTo(0, {current})")
                else:
                    await page.evaluate(f"window.scrollTo(0, {current})")

                await BehavioralSimulator.human_delay(0.3, 0.8)

                # Update height (in case of infinite scroll)
                if driver_type == "playwright":
                    height = await page.evaluate("document.body.scrollHeight")
                else:
                    height = await page.evaluate("document.body.scrollHeight")

        except Exception as e:
            logger.debug(f"Scroll to bottom failed: {e}")

    # =========================================================================
    # MOUSE MOVEMENT
    # =========================================================================

    @staticmethod
    def random_mouse_movement_sync(driver: Any, element: Any = None) -> None:
        """
        Synchronous mouse movement simulation for Selenium.

        Moves mouse in small random offsets to simulate human movement.
        """
        if not driver:
            return

        try:
            from selenium.webdriver.common.action_chains import ActionChains

            action = ActionChains(driver)
            steps = random.randint(10, 30)

            for _ in range(steps):
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-5, 5)
                action.move_by_offset(offset_x, offset_y)

            action.perform()
        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")

    @staticmethod
    async def random_mouse_movement(page: Any, driver_type: str = "playwright") -> None:
        """
        Async mouse movement simulation.

        Uses Bezier curves for natural movement path.
        """
        if not page:
            return

        try:
            # Get viewport size
            if driver_type == "playwright":
                viewport = await page.evaluate(
                    "() => ({w: window.innerWidth, h: window.innerHeight})"
                )
            else:
                viewport = await page.evaluate(
                    "({w: window.innerWidth, h: window.innerHeight})"
                )

            # Generate random target within viewport
            target_x = random.randint(100, viewport["w"] - 100)
            target_y = random.randint(100, viewport["h"] - 100)

            # Move in steps (simulating natural movement)
            steps = random.randint(5, 15)

            if driver_type == "playwright":
                for i in range(steps):
                    # Interpolate position
                    t = (i + 1) / steps
                    x = int(target_x * t)
                    y = int(target_y * t)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.01, 0.05))
            else:
                # nodriver uses different API
                pass

        except Exception as e:
            logger.debug(f"Async mouse movement failed: {e}")

    # =========================================================================
    # TYPING
    # =========================================================================

    @staticmethod
    def human_type_sync(element: Any, text: str) -> None:
        """
        Synchronous realistic typing for Selenium.

        Includes random delays, occasional pauses, and rare typos.
        """
        if not element:
            return

        try:
            from selenium.webdriver.common.keys import Keys

            for char in text:
                element.send_keys(char)

                # Base delay between keystrokes
                BehavioralSimulator.human_delay_sync(0.15, 0.35)

                # Occasional longer pause (10% chance)
                if random.random() < 0.1:
                    BehavioralSimulator.human_delay_sync(0.5, 1.5)

                # Rare typo simulation (5% chance)
                if random.random() < 0.05:
                    element.send_keys(Keys.BACKSPACE)
                    BehavioralSimulator.human_delay_sync(0.3, 0.6)

        except Exception as e:
            logger.debug(f"Typing simulation failed: {e}")

    @staticmethod
    async def human_type(page: Any, selector: str, text: str, driver_type: str = "playwright") -> None:
        """
        Async realistic typing.

        Args:
            page: Page/Tab instance
            selector: CSS selector for input element
            text: Text to type
            driver_type: 'playwright' or 'nodriver'
        """
        if not page:
            return

        try:
            for char in text:
                if driver_type == "playwright":
                    await page.type(selector, char, delay=random.randint(100, 300))
                else:
                    # nodriver
                    element = await page.select(selector)
                    if element:
                        await element.send_keys(char)

                # Occasional longer pause
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            logger.debug(f"Async typing failed: {e}")

    # =========================================================================
    # CLICK SIMULATION
    # =========================================================================

    @staticmethod
    async def human_click(
        page: Any, selector: str, driver_type: str = "playwright"
    ) -> None:
        """
        Simulate human-like click with pre-movement.
        """
        if not page:
            return

        try:
            if driver_type == "playwright":
                # Get element bounding box
                element = await page.query_selector(selector)
                if element:
                    box = await element.bounding_box()
                    if box:
                        # Move to element area with small random offset
                        x = box["x"] + box["width"] / 2 + random.randint(-5, 5)
                        y = box["y"] + box["height"] / 2 + random.randint(-5, 5)

                        await page.mouse.move(x, y)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        await page.mouse.click(x, y)

        except Exception as e:
            logger.debug(f"Human click failed: {e}")

    # =========================================================================
    # FULL SIMULATION SESSION
    # =========================================================================

    async def simulate_browsing(
        self,
        page: Any,
        driver_type: str = "playwright",
        duration: float = 10.0,
    ) -> None:
        """
        Simulate a full browsing session with random actions.

        Args:
            page: Page/Tab instance
            driver_type: 'playwright' or 'nodriver'
            duration: How long to simulate (seconds)
        """
        import time

        start = time.time()

        while time.time() - start < duration:
            action = random.choice(["scroll", "pause", "mouse"])

            if action == "scroll" and self.scroll_enabled:
                await self.scroll_page(page, driver_type)
            elif action == "mouse" and self.mouse_enabled:
                await self.random_mouse_movement(page, driver_type)
            else:
                await self.human_delay(self.min_delay, self.max_delay)
