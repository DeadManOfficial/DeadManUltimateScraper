"""
Weaponry: Automated API Signup and Management
==============================================
NASA Standard: Resource lifecycle management.
Assists the user in replenishing "Free Forever" API keys.
"""

import logging
import webbrowser

logger = logging.getLogger("Weaponry")

class WeaponryManager:
    """
    Manages the acquisition of fresh API weaponry (keys).
    """

    SERVICES = [
        {
            'name': 'OpenRouter',
            'url': 'https://openrouter.ai/keys',
            'benefit': 'Perpetual access to free models (DeepSeek, Mistral)',
        },
        {
            'name': 'Groq',
            'url': 'https://console.groq.com/keys',
            'benefit': '14,400 requests/day free',
        },
        {
            'name': 'Mistral',
            'url': 'https://console.mistral.ai/api-keys/',
            'benefit': '1 Billion token free grant',
        }
    ]

    def open_armory(self):
        """
        Open all signup pages in the default browser.
        """
        logger.info("Opening the Armory (API Signup Pages)...")
        for service in self.SERVICES:
            logger.info(f"Opening {service['name']} - {service['benefit']}")
            webbrowser.open(service['url'])

    def get_status_report(self, config_api_keys: dict) -> list[dict[str, str]]:
        """
        Check which weapons are currently loaded.
        """
        report = []
        for service in self.SERVICES:
            name_lower = service['name'].lower()
            report.append({
                "service": service['name'],
                "status": "LOADED" if name_lower in config_api_keys else "MISSING",
                "benefit": service['benefit']
            })
        return report
