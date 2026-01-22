"""
Configuration Management
========================
Centralized settings for all scraper components.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class FetchConfig(BaseModel):
    """Fetch layer configuration."""

    # Layer priorities (order of fallback)
    layers: list[Literal["curl_cffi", "camoufox", "nodriver", "chromedriver", "tor", "captcha"]] = [
        "curl_cffi",
        "camoufox",
        "chromedriver",
        "tor",
    ]

    # Timeouts (seconds)
    request_timeout: int = 30
    page_load_timeout: int = 60
    connect_timeout: int = 10

    # Retries per layer
    max_retries_per_layer: int = 2

    # Concurrent requests
    max_concurrent: int = 10
    max_concurrent_per_domain: int = 2

    # Rate limiting
    download_delay: float = 0.5  # seconds between requests to same domain
    randomize_delay: bool = True
    delay_variance: float = 0.5  # 0.5 means delay * (0.5 to 1.5)


class BrowserPoolConfig(BaseModel):
    """Browser pool configuration (3-tier)."""

    # Permanent browsers (always running)
    permanent_count: int = 2

    # Hot browsers (warmed up, ready to use)
    hot_count: int = 3

    # Cold browsers (spawned on demand)
    cold_max: int = 10

    # Headless mode
    headless: bool = True

    # Browser type
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"

    # Page recycling
    pages_per_browser: int = 50  # Restart browser after N pages


class TORConfig(BaseModel):
    """TOR configuration."""

    enabled: bool = True
    method: Literal["docker", "portable", "system", "cloud"] = "system"

    # Docker settings
    docker_image: str = "dperson/torproxy"
    docker_container_name: str = "deadman-tor"

    # Connection
    socks_host: str = "127.0.0.1"
    socks_port: int = 9050
    control_port: int = 9051

    # Circuit management
    circuit_renew_interval: int = 300  # seconds
    renew_on_block: bool = True

    # Timeouts
    connect_timeout: int = 30


class ProxyConfig(BaseModel):
    """Proxy rotation configuration."""

    enabled: bool = False
    type: Literal["datacenter", "residential", "mobile", "mixed"] = "datacenter"

    # Proxy sources
    proxy_file: str | None = None
    proxy_api: str | None = None
    proxy_list: list[str] = Field(default_factory=list)

    # Rotation strategy
    rotate_on_block: bool = True
    rotate_interval: int = 0  # 0 = don't rotate on interval
    max_uses_per_proxy: int = 100

    # Tiered rotation (Crawlee pattern)
    tier_ratios: dict[str, float] = {"datacenter": 0.7, "residential": 0.25, "mobile": 0.05}


class CaptchaConfig(BaseModel):
    """CAPTCHA solver configuration."""

    enabled: bool = False
    provider: Literal["2captcha", "anticaptcha", "capsolver", "local"] = "2captcha"
    api_key: str | None = None

    # Strategy
    solve_recaptcha: bool = True
    solve_hcaptcha: bool = True
    solve_turnstile: bool = True
    solve_text: bool = True

    # Timeouts
    wait_timeout: int = 60
    polling_interval: int = 5


class StealthConfig(BaseModel):
    """Stealth/anti-detection configuration."""

    # JavaScript injection
    inject_stealth: bool = True

    # Fingerprint spoofing
    spoof_canvas: bool = True
    spoof_webgl: bool = True
    spoof_audio: bool = True

    # TLS fingerprinting (JA3/JA4)
    impersonate_browser: Literal["chrome", "firefox", "safari", "edge"] = "chrome"
    impersonate_version: str = "120"

    # Behavioral simulation
    simulate_human: bool = True
    human_delay_min: float = 1.0
    human_delay_max: float = 3.0
    scroll_behavior: bool = True
    mouse_movement: bool = True


class QuotaConfig(BaseModel):
    """NASA Standard: Strict quota monitoring for Free Forever compliance."""
    max_daily_requests: int = 14000  # Based on Groq limit
    max_monthly_tokens: int = 900000000 # Based on Mistral limit (90% threshold)
    enable_caching: bool = True
    cache_dir: str = "data/cache"

class LLMConfig(BaseModel):
    """FREE LLM router configuration."""

    # Primary provider preference
    primary: Literal["mistral", "groq", "cerebras", "ollama"] = "mistral"

    # Fallback chain
    fallback_chain: list[str] = ["mistral", "groq", "cerebras", "ollama"]

    # Provider-specific settings
    mistral_model: str = "mistral-small"
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_model: str = "llama-3.3-70b"
    ollama_model: str = "llama3.2"

    # Quota thresholds (switch before hitting limit)
    quota_threshold: float = 0.9  # Switch at 90% usage

    # Task routing
    heavy_tasks_provider: str = "mistral"  # 1B tokens
    fast_tasks_provider: str = "groq"  # Fast inference
    offline_provider: str = "ollama"  # Local


class ExtractionConfig(BaseModel):
    """Content extraction configuration."""

    # Default strategy
    default_strategy: Literal["css", "xpath", "regex", "llm", "auto"] = "auto"

    # Content processors
    enable_pruning: bool = True
    enable_bm25: bool = True
    enable_chunking: bool = True

    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Link scoring
    score_links: bool = True
    min_link_score: float = 0.3


class OutputConfig(BaseModel):
    """Output pipeline configuration."""

    # Default format
    default_format: Literal["json", "markdown", "csv", "postgres", "obsidian"] = "json"

    # Output directory
    output_dir: str = "./output"

    # PostgreSQL
    postgres_uri: str = "postgresql://localhost/deadman_research"

    # Obsidian
    obsidian_vault: str = os.getenv("OBSIDIAN_VAULT", "./vault")
    obsidian_folder: str = "Scraped"


class DiscoveryConfig(BaseModel):
    """Multi-engine search configuration."""

    # Engines to use
    clearnet_engines: list[str] = [
        "google",
        "duckduckgo",
        "brave",
        "bing",
        "github",
        "archive",
    ]
    darknet_engines: list[str] = ["ahmia", "torch", "haystak", "darksearch"]

    # Search settings
    max_results_per_engine: int = 50
    deduplicate: bool = True

    # Rate limiting per engine
    search_delay: float = 2.0


class Config(BaseModel):
    """
    Master configuration for DEADMAN ULTIMATE SCRAPER.

    Load from YAML:
        config = Config.from_yaml("config/default.yaml")

    Environment override:
        DEADMAN_FETCH_MAX_CONCURRENT=20
    """

    fetch: FetchConfig = Field(default_factory=FetchConfig)
    browser_pool: BrowserPoolConfig = Field(default_factory=BrowserPoolConfig)
    tor: TORConfig = Field(default_factory=TORConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig)
    stealth: StealthConfig = Field(default_factory=StealthConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)

    # API Keys (loaded from environment or secrets file)
    api_keys: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load configuration from YAML file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration with environment variable overrides."""
        config = cls()

        # Override from DEADMAN_* environment variables
        prefix = "DEADMAN_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Parse key like DEADMAN_FETCH_MAX_CONCURRENT
                parts = key[len(prefix) :].lower().split("_", 1)
                if len(parts) == 2:
                    section, setting = parts
                    section_config = getattr(config, section, None)
                    if section_config and hasattr(section_config, setting):
                        # Type coercion
                        current = getattr(section_config, setting)
                        if isinstance(current, bool):
                            value = value.lower() in ("true", "1", "yes")
                        elif isinstance(current, int):
                            value = int(value)
                        elif isinstance(current, float):
                            value = float(value)
                        setattr(section_config, setting, value)

        return config

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    def load_api_keys(self, secrets_file: str | Path | None = None) -> None:
        """
        Load API keys from secrets file or environment.

        Default secrets file: ~/.secrets/DEADMAN_API_MASTER.md or env SECRETS_FILE
        """
        if secrets_file is None:
            secrets_file = Path(os.getenv("SECRETS_FILE", Path.home() / ".secrets" / "DEADMAN_API_MASTER.md"))

        # Try loading from environment first
        env_keys = {
            "mistral": os.getenv("MISTRAL_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "cerebras": os.getenv("CEREBRAS_API_KEY"),
            "github": os.getenv("GITHUB_TOKEN"),
            "pexels": os.getenv("PEXELS_API_KEY"),
            "pixabay": os.getenv("PIXABAY_API_KEY"),
        }

        for key, value in env_keys.items():
            if value:
                self.api_keys[key] = value

        # Parse secrets file if it exists
        secrets_path = Path(secrets_file)
        if secrets_path.exists():
            content = secrets_path.read_text(encoding="utf-8")

            # Extract API keys using section-based parsing
            import re

            # Find each section and extract API key from within that section
            sections = {
                "mistral": r"## MISTRAL.*?API Key:\s*(\S+)",
                "groq": r"## GROQ.*?API Key:\s*(\S+)",
                "cerebras": r"## CEREBRAS.*?API Key:\s*(\S+)",
                "pexels": r"## PEXELS.*?API Key:\s*(\S+)",
                "pixabay": r"## PIXABAY.*?API Key:\s*(\S+)",
                "github": r"Fine-grained PAT:\s*(github_pat_\S+)",
                "youtube": r"## YOUTUBE DATA API.*?API Key:\s*(\S+)",
                "freesound": r"## FREESOUND.*?API Key:\s*(\S+)",
                "nasa": r"## NASA APOD.*?API Key:\s*(\S+)",
                "json2video": r"## JSON2VIDEO.*?API Key:\s*(\S+)",
            }

            for key, pattern in sections.items():
                if key not in self.api_keys:
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        self.api_keys[key] = match.group(1)
