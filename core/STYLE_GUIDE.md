# NASA-Standard Style Guide & Design System
**Project:** DEATH INCARNATE
**Theme:** BLACK HAT / NASA-8739.12

## 1. Code Style (NASA Standard)
### 1.1 Typing
Every function and method **must** include full Python 3.10+ type hints.
```python
def execute_mission(url: str, params: MissionParams) -> Dict[str, Any]:
```

### 1.2 Documentation
Every class and module must start with a NASA-standard header.
```python
"""
[Module Name]
=========================
NASA Standard: [Standard ID]
Purpose: [Clear, concise description]
"""
```

### 1.3 Complexity
- Cyclomatic complexity must remain **under 10**.
- Functions exceeding 50 lines must be refactored into components.

## 2. Visual Identity (Black Hat UI/UX)
### 2.1 Terminal Output (Theming)
All CLI tools must use the `rich` library with the following palette:
- **Success:** `bold green` (Matrix style)
- **Warning:** `bold yellow` (Telemetry alert)
- **Critical/Failure:** `bold red` (System breach)
- **Headers:** `bold cyan` (NASA Command)

### 2.2 Logging
Logs must be atomic and follow the established `nasa_audit_trail.jsonl` format.

## 3. Component Library
Reusable components must be stored in `deadman_scraper/utils/` or `deadman_scraper/core/`.
- **Sanitizer:** For all input cleaning.
- **AuditLogger:** For all event persistence.
- **SiteScraper:** Base class for all site-specific logic.

## 4. Manifest Adherence
Before every push, the `MissionStacker` quality gate verifies adherence to these standards.
