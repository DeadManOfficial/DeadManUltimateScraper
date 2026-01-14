# DEADMAN ULTIMATE SCRAPER - NASA Standard Design Specification
**Version:** 2.0.0 (God Mode / Absolute Freedom)
**Compliance:** NASA-8739.12 (Software Coding Standards)

## 1. Architectural Overview
The DeadMan Ultimate Scraper is a multi-layer, fault-tolerant intelligence gathering engine designed for autonomous discovery and exploitation of data sources across clearnet and darknet environments.

### 1.1 Core Components
- **CentralScraper (God Module):** The high-level entry point coordinating all subsystems.
- **AdaptiveDownloader:** A 5-layer fetch stack with automatic fallback (TLS -> Stealth Browser -> Selenium -> TOR -> CAPTCHA).
- **SignalManager:** Decoupled event bus for NASA-standard traceability.
- **AuditLogger:** Immutable, timestamped trail of all system events.
- **ProxyManager:** Health-aware rotation of residential and mobile circuits.

## 2. Design Principles
### 2.1 Modularity and Coupling
- Each site-specific scraper (Costco, Sentinel) inherits from a common `SiteScraper` base class.
- Low coupling through dependency injection (Config, Signals, Managers).

### 2.2 Fault Tolerance
- Aggressive retry with exponential backoff and jitter.
- TCP KeepAlive implementation to prevent idle timeout connection resets.
- Circuit renewal protocols for TOR and Proxy subsystems.

### 2.3 Security and Stealth
- **TLS/Fingerprint Spoofing:** JA3/JA4 impersonation using `curl_cffi`.
- **Evasion Injection:** Advanced JS injected via CDP to bypass WebDriver and browser-layer detection.
- **Secret Scanning:** Integrated `Bloodhound` module for real-time identification of leaked keys and SynthID markers.

## 3. Engineering Standards
- **Cyclomatic Complexity:** Targeted < 10 for all core functions.
- **Typing:** Strict Python type-hinting throughout for static analysis.
- **Traceability:** Requirement-to-code traceability via Signal enumeration.

## 4. Maintenance and Scaling
- **Persistence:** SQLite-backed priority queue with ACID-compliant transactions.
- **Intelligence Lifecycle:** Discovery -> Enqueue -> Scrape -> Analyze -> Store.
