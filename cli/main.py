#!/usr/bin/env python3
"""DEADMAN ULTIMATE SCRAPER - CLI Interface"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
        # Reconfigure stdout/stderr for UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    from .deep_commands import register_deep_commands
    HAS_DEEP = True
except ImportError:
    HAS_DEEP = False

try:
    from .darkweb_commands import register_darkweb_commands
    HAS_DARKWEB = True
except ImportError:
    HAS_DARKWEB = False

app = typer.Typer(name="deadman", help="DEADMAN ULTIMATE SCRAPER // DEATH INCARNATE", add_completion=False)
console = Console(legacy_windows=(sys.platform == "win32"), theme=None)

# --- BLACK HAT THEME CONFIG ---
HEADER_STYLE = "bold cyan"
SUCCESS_STYLE = "bold green"
FAIL_STYLE = "bold red"
INFO_STYLE = "bold white"
PANEL_STYLE = "green"

# Register deep scraping commands
if HAS_DEEP:
    register_deep_commands(app)

# Register dark web commands
if HAS_DARKWEB:
    register_darkweb_commands(app)

def version_callback(value: bool):
    if value:
        from deadman_scraper import __version__
        rprint(f"[{HEADER_STYLE}]DEADMAN ULTIMATE SCRAPER[/] v{__version__} // [bold red]DEATH INCARNATE[/]")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(None, "--version", "-v", callback=version_callback, help="Show version")):
    """
    DEADMAN ULTIMATE SCRAPER: NASA-Standard Intelligence Engine.
    """
    pass

@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
    format: str = typer.Option("json", "-f", "--format", help="Output format"),
    tor: bool = typer.Option(False, "--tor", help="Force TOR routing"),
    extract: Optional[str] = typer.Option(None, "-e", "--extract", help="CSS selector"),
    llm: bool = typer.Option(False, "--llm", help="Use LLM for extraction"),
    verbose: bool = typer.Option(False, "-V", "--verbose", help="Verbose output"),
):
    """Scrape a single URL with adaptive bypass."""
    async def _scrape():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.load_api_keys()
        console.print(f"[{HEADER_STYLE}]Initiating Scrape Protocols:[/] [white]{url}[/]")
        async with Engine(config) as engine:
            result = await engine.scrape(url, use_tor=tor, extract_strategy=extract, use_llm=llm)
        if result.success:
            console.print(f"\n[{SUCCESS_STYLE}]Bypass Successful![/] Target extracted via Layer {result.fetch_layer}")
            if verbose:
                console.print(f"Status: {result.status_code}")
                console.print(f"Content-Type: {result.content_type}")
                console.print(f"Timing: {result.timing.get('total', 0):.2f}s")
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                data = {"url": result.url, "status_code": result.status_code, "content_type": result.content_type, "fetch_layer": result.fetch_layer, "content": result.content, "extracted": result.extracted}
                with open(output, "w", encoding="utf-8") as f:
                    if format == "json":
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    elif format == "md":
                        f.write("# " + url + "\n\n" + (result.content or ""))
                    else:
                        f.write(result.content or "")
                console.print(f"[{INFO_STYLE}]Intelligence Persisted:[/] {output}")
            else:
                if result.content:
                    preview = result.content[:500] + "..." if len(result.content) > 500 else result.content
                    console.print(Panel(preview, title="Intelligence Preview", border_style=PANEL_STYLE))
        else:
            console.print(f"\n[{FAIL_STYLE}]Protocols Failed:[/] {result.error}")
            raise typer.Exit(1)
    asyncio.run(_scrape())

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    engines: Optional[str] = typer.Option(None, "--engines", help="Engines"),
    max_results: int = typer.Option(20, "-n", "--max", help="Max results"),
    scrape_top: int = typer.Option(0, "--scrape-top", help="Scrape top N"),
    darkweb: bool = typer.Option(False, "--darkweb", help="Dark web engines"),
    filter_llm: bool = typer.Option(False, "--filter-llm", help="LLM filtering"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Multi-engine search with optional intelligence extraction."""
    async def _search():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.load_api_keys()
        engine_list = engines.split(",") if engines else None
        console.print(f"\n[{HEADER_STYLE}]Initiating Wide-Spectrum Search:[/] [white]{query}[/]")
        async with Engine(config) as engine:
            if scrape_top > 0:
                console.print(f"[{INFO_STYLE}]Exploiting top {scrape_top} targets...[/]\n")
                results = []
                async for result in engine.search_and_scrape(query, engines=engine_list, max_results=max_results, scrape_top=scrape_top, darkweb=darkweb, filter_llm=filter_llm):
                    status = f"[{SUCCESS_STYLE}]OK[/]" if result.success else f"[{FAIL_STYLE}]FAIL[/]"
                    console.print(f"  {status} {result.url}")
                    results.append({"url": result.url, "success": result.success, "content_preview": result.content[:200] if result.content else None})
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with open(output, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    console.print(f"\n[{INFO_STYLE}]Data Persisted:[/] {output}")
            else:
                from deadman_scraper.discovery.aggregator import SearchAggregator
                aggregator = SearchAggregator(config)
                results = await aggregator.search(query, engines=engine_list, max_results=max_results, darkweb=darkweb)
                console.print(f"\n[{SUCCESS_STYLE}]Found {len(results)} intelligence vectors[/]\n")
                table = Table(title="Intelligence Inventory", border_style=PANEL_STYLE)
                table.add_column("Title", style=INFO_STYLE)
                table.add_column("URL", style="blue")
                table.add_column("Engine")
                for r in results[:20]:
                    table.add_row(r.get("title", "")[:50], r.get("url", "")[:60], r.get("engine", ""))
                console.print(table)
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with open(output, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    console.print(f"\n[{INFO_STYLE}]Inventory Persisted:[/] {output}")
    asyncio.run(_search())

@app.command()
def batch(
    urls_file: Path = typer.Argument(..., help="File with URLs"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
    format: str = typer.Option("json", "-f", "--format", help="Output format"),
    concurrency: int = typer.Option(5, "-c", "--concurrency", help="Concurrent requests"),
    tor: bool = typer.Option(False, "--tor", help="Force TOR routing"),
):
    """Batch execute scrape protocols from target file."""
    if not urls_file.exists():
        console.print(f"[{FAIL_STYLE}]Error:[/] Target manifest not found: {urls_file}")
        raise typer.Exit(1)
    urls = [line.strip() for line in urls_file.read_text().splitlines() if line.strip()]
    console.print(f"\n[{HEADER_STYLE}]Initiating Batch Exploitation:[/] [white]{len(urls)} targets[/]\n")
    async def _batch():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.fetch.max_concurrent = concurrency
        results, success, failed = [], 0, 0
        async with Engine(config) as engine:
            async for result in engine.scrape_many(urls, meta={"force_tor": tor}):
                if result.success:
                    success += 1
                    stat = f"[{SUCCESS_STYLE}]OK[/]"
                else:
                    failed += 1
                    stat = f"[{FAIL_STYLE}]FAIL[/]"
                console.print(f"  {stat} {result.url}")
                results.append({"url": result.url, "success": result.success, "status_code": result.status_code, "error": result.error, "content_length": len(result.content) if result.content else 0})
        console.print(f"\n[{SUCCESS_STYLE}]Success: {success}[/] | [{FAIL_STYLE}]Failed: {failed}[/]")
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            console.print(f"[{INFO_STYLE}]Batch Data Persisted:[/] {output}")
    asyncio.run(_batch())

@app.command()
def tor(action: str = typer.Argument("status", help="Action: start/stop/restart/status")):
    """Manage TOR proxy circuit integrity."""
    async def _tor():
        from deadman_scraper.core.config import Config
        from deadman_scraper.fetch.tor import TORManager
        config = Config.from_env()
        manager = TORManager(config.tor)
        if action == "start":
            console.print(f"[{HEADER_STYLE}]Activating TOR Circuit...[/]")
            ok = await manager.start()
            if ok:
                ip = await manager.get_exit_ip()
                console.print(f"[{SUCCESS_STYLE}]Circuit Established![/]")
                console.print(f"[{INFO_STYLE}]Proxy:[/] {manager.proxy_url}")
                if ip:
                    console.print(f"[{INFO_STYLE}]Exit IP:[/] {ip}")
            else:
                console.print(f"[{FAIL_STYLE}]Activation Failed[/]")
                raise typer.Exit(1)
        elif action == "stop":
            console.print(f"[{HEADER_STYLE}]Deactivating TOR Circuit...[/]")
            await manager.stop()
            console.print(f"[{SUCCESS_STYLE}]Circuit Severed[/]")
        elif action == "restart":
            console.print(f"[{HEADER_STYLE}]Renewing Identity...[/]")
            ok = await manager.renew_circuit()
            if ok:
                ip = await manager.get_exit_ip()
                console.print(f"[{SUCCESS_STYLE}]Identity Spoofed![/]")
                if ip:
                    console.print(f"[{INFO_STYLE}]New Exit IP:[/] {ip}")
            else:
                console.print(f"[{FAIL_STYLE}]Renewal Failed[/]")
        else:
            st = await manager.status()
            table = Table(title="TOR Circuit Telemetry", border_style=PANEL_STYLE)
            table.add_column("Property", style=HEADER_STYLE)
            table.add_column("Value")
            table.add_row("Docker Engine", f"[{SUCCESS_STYLE}]Operational[/]" if st.docker_available else f"[{FAIL_STYLE}]Offline[/]")
            table.add_row("Circuit Status", f"[{SUCCESS_STYLE}]Active[/]" if st.running else f"[{FAIL_STYLE}]Inactive[/]")
            if st.proxy_url:
                table.add_row("Access Point", st.proxy_url)
            if st.exit_ip:
                table.add_row("Current Exit IP", st.exit_ip)
            console.print(table)
    asyncio.run(_tor())

@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show/set/reset"),
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
):
    """Manage mission configuration parameters."""
    from deadman_scraper.core.config import Config
    import yaml
    config_file = Path("config/default.yaml")
    if action == "show":
        cfg = Config.from_env()
        console.print(Panel(yaml.dump(cfg.model_dump(), default_flow_style=False), title="System Configuration", border_style=PANEL_STYLE))
    elif action == "set":
        if not key or not value:
            console.print(f"[{FAIL_STYLE}]Usage:[/] deadman config set <key> <value>")
            raise typer.Exit(1)
        console.print(f"[{INFO_STYLE}]Updating parameter:[/] {key} = {value}")
    elif action == "reset":
        console.print(f"[{HEADER_STYLE}]Resetting System to Factory Defaults...[/]")
        cfg = Config()
        cfg.to_yaml(config_file)
        console.print(f"[{SUCCESS_STYLE}]Reset Complete![/] State persisted to {config_file}")

@app.command()
def stats():
    """Display real-time quota telemetry and usage analytics."""
    async def _stats():
        from deadman_scraper.core.config import Config
        from deadman_scraper.ai.llm_router import FreeLLMRouter
        cfg = Config.from_env()
        cfg.load_api_keys()
        router = FreeLLMRouter(cfg.llm, cfg.api_keys)
        st = router.get_quota_status()
        table = Table(title="Weaponry Quota Telemetry", border_style=PANEL_STYLE)
        table.add_column("Source", style=HEADER_STYLE)
        table.add_column("Used", justify="right")
        table.add_column("Remaining", justify="right")
        table.add_column("Limit", justify="right")
        table.add_column("Cycle")
        table.add_column("Attrition", justify="right")
        for name, info in st.items():
            pct = info["percent_used"]
            pct_str = f"{pct:.1f}%"
            if pct > 90:
                pct_str = f"[{FAIL_STYLE}]{pct_str}[/]"
            elif pct > 70:
                pct_str = f"[yellow]{pct_str}[/]"
            else:
                pct_str = f"[{SUCCESS_STYLE}]{pct_str}[/]"
            table.add_row(name.capitalize(), str(info["used"]), str(info["remaining"]), str(info["limit"]), info["period"], pct_str)
        console.print(table)
    asyncio.run(_stats())

def run():
    app()

if __name__ == "__main__":
    run()
