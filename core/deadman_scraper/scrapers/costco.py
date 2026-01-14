"""
Costco Warehouse Scraper
========================
NASA Standard: Specialized scraper for Costco warehouse intelligence.
Inherits from SiteScraper base class.
"""

import json
import logging
import re
from typing import Any

from deadman_scraper.scrapers.base import SiteScraper

logger = logging.getLogger("CostcoScraper")

class CostcoScraper(SiteScraper):
    """
    Scraper for extracting warehouse-specific information from Costco.
    """

    async def scrape(self, item_id: str) -> dict[str, Any]:
        """
        Extract complete warehouse location data for a Costco item.
        """
        logger.info(f"Starting Costco scrape for item: {item_id}")

        # 1. Fetch Product Page
        product_url = f'https://app.warehouserunner.com/costco/{item_id}'
        result = await self._fetch(product_url, use_llm=False)

        if not result.success or not result.content:
            logger.error(f"Failed to fetch product page for {item_id}")
            return {"error": "Product fetch failed"}

        # 2. Extract Data
        product_data = self._parse_product_page(result.content, item_id)

        # 3. Fetch Warehouse Details if found
        warehouses = []
        if product_data.get('first_warehouse_url'):
            wh_url = f"https://app.warehouserunner.com{product_data['first_warehouse_url']}"
            wh_result = await self._fetch(wh_url)
            if wh_result.success and wh_result.content:
                wh_details = self._parse_warehouse_details(wh_result.content, product_data['first_warehouse_url'])
                if wh_details:
                    warehouses.append(wh_details)

        return {
            **product_data,
            "warehouses": warehouses,
            "warehouses_found": len(warehouses)
        }

    def _parse_product_page(self, html: str, item_id: str) -> dict[str, Any]:
        """Extract product-level data."""
        # Ported logic from warehouse_detail_scraper.py
        discount_match = re.search(r'discount_count["\\]*s*:+(\d+)', html)
        discount_count = int(discount_match.group(1)) if discount_match else 0

        product_match = re.search(r'enriched_name["\\]*s*:+([^"\\]+)', html)
        product_name = product_match.group(1).replace('\\', '') if product_match else ''

        # Store ID and Name for first warehouse
        first_warehouse_url = None
        store_id_match = re.search(r'store_id\":(\d+)', html)
        store_name_match = re.search(r'store_name\":\"([A-Za-z\s]+)\"', html)

        if store_id_match and store_name_match:
            store_id = store_id_match.group(1)
            store_name = store_name_match.group(1).strip().lower().replace(' ', '-')
            first_warehouse_url = f'/store/{store_name}-{store_id}'

        return {
            'item_id': item_id,
            'name': product_name,
            'discount_count': discount_count,
            'first_warehouse_url': first_warehouse_url
        }

    def _parse_warehouse_details(self, html: str, url_path: str) -> dict[str, Any] | None:
        """Extract detailed warehouse information from schema data."""
        # Extract warehouse number
        wh_num_match = re.search(r'-(\d+)$', url_path)
        wh_num = int(wh_num_match.group(1)) if wh_num_match else None

        # Extract LD+JSON
        schema_match = re.search(
            r'name="script-type-application/ld\+json"\s+content="([^"]+)"',
            html
        )
        if not schema_match:
            return None

        import html as html_module
        schema_json = html_module.unescape(schema_match.group(1))

        try:
            data = json.loads(schema_json)
            address = data.get('address', {})
            geo = data.get('geo', {})

            return {
                'warehouse_number': wh_num,
                'name': data.get('name', ''),
                'street_address': address.get('streetAddress', ''),
                'city': address.get('addressLocality', ''),
                'state': address.get('addressRegion', ''),
                'zip_code': address.get('postalCode', ''),
                'latitude': geo.get('latitude'),
                'longitude': geo.get('longitude'),
                'phone': data.get('telephone', '')
            }
        except json.JSONDecodeError:
            return None
