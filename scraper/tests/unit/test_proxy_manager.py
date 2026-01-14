"""
NASA-Standard Unit Tests: ProxyManager
======================================
Tests for proxy rotation, health tracking, and circuit renewal.
"""

import pytest
from unittest.mock import MagicMock, patch
from deadman_scraper.fetch.proxy_manager import ProxyManager, ProxyHealth
from deadman_scraper.core.config import Config

@pytest.fixture
def mock_config():
    config = Config()
    config.proxy.enabled = True
    config.proxy.type = "residential"
    config.proxy.proxy_list = ["http://proxy1.com", "http://proxy2.com"]
    config.proxy.proxy_file = None
    config.tor.control_port = 9051
    return config

def test_proxy_loading(mock_config):
    """Verify proxies are loaded correctly from config."""
    pm = ProxyManager(mock_config)
    assert len(pm.proxies) == 2
    assert "http://proxy1.com" in pm.proxies
    assert pm.proxies["http://proxy1.com"].type == "residential"

def test_proxy_rotation(mock_config):
    """Verify round-robin rotation works correctly."""
    pm = ProxyManager(mock_config)
    p1 = pm.get_proxy()
    p2 = pm.get_proxy()
    p3 = pm.get_proxy()
    
    assert p1 != p2
    assert p1 == p3  # Circular rotation

def test_proxy_blocking(mock_config):
    """Verify proxies are skipped when blocked."""
    pm = ProxyManager(mock_config)
    proxy_url = "http://proxy1.com"
    pm.report_failure(proxy_url, is_block=True)
    
    # Ensure blocked proxy is not selected
    for _ in range(10):
        assert pm.get_proxy() == "http://proxy2.com"

def test_proxy_recovery(mock_config):
    """Verify proxies can recover from failure."""
    pm = ProxyManager(mock_config)
    proxy_url = "http://proxy1.com"
    pm.report_failure(proxy_url, is_block=True)
    assert pm.proxies[proxy_url].is_blocked is True
    
    pm.report_success(proxy_url)
    assert pm.proxies[proxy_url].is_blocked is False
    assert pm.proxies[proxy_url].success_count == 1

@pytest.mark.asyncio
async def test_tor_circuit_renewal(mock_config):
    """Verify TOR circuit renewal attempt (mocked)."""
    with patch("stem.control.Controller.from_port") as mock_controller:
        pm = ProxyManager(mock_config)
        await pm.renew_tor_circuit()
        # Basic check that mock was called
        assert mock_controller.called
