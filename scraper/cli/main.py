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

app = typer.Typer(name="deadman", help="DEADMAN ULTIMATE SCRAPER", add_completion=False)
console = Console(legacy_windows=(sys.platform == "win32"))

# Register deep scraping commands
if HAS_DEEP:
    register_deep_commands(app)

def version_callback(value: bool):
    if value:
        from deadman_scraper import __version__
        rprint(f"[bold cyan]DEADMAN ULTIMATE SCRAPER[/bold cyan] v{__version__}")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(None, "--version", "-v", callback=version_callback, help="Show version")):
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
    """Scrape a single URL."""
    async def _scrape():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.load_api_keys()
        console.print(f"[cyan]Scraping {url}...[/cyan]")
        async with Engine(config) as engine:
            result = await engine.scrape(url, use_tor=tor, extract_strategy=extract, use_llm=llm)
        if result.success:
            console.print(f"\n[green]Success![/green] Layer {result.fetch_layer}")
            if verbose:
                console.print(f"Status: {result.status_code}")
                console.print(f"Content-Type: {result.content_type}")
                console.print(f"Timing: {result.timing.get('total', 0):.2f}s")
            if output:
                data = {"url": result.url, "status_code": result.status_code, "content_type": result.content_type, "fetch_layer": result.fetch_layer, "content": result.content, "extracted": result.extracted}
                with open(output, "w", encoding="utf-8") as f:
                    if format == "json":
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    elif format == "md":
                        f.write("# " + url + "\n\n" + (result.content or ""))
                    else:
                        f.write(result.content or "")
                console.print(f"Saved to: {output}")
                console.print(f"Content length: {len(result.content) if result.content else 0} chars")
            else:
                if result.content:
                    preview = result.content[:500] + "..." if len(result.content) > 500 else result.content
                    console.print(Panel(preview, title="Content Preview"))
        else:
            console.print(f"\n[red]Failed:[/red] {result.error}")
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
    """Multi-engine search with optional scraping."""
    async def _search():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.load_api_keys()
        engine_list = engines.split(",") if engines else None
        console.print(f"\n[cyan]Searching:[/cyan] {query}")
        async with Engine(config) as engine:
            if scrape_top > 0:
                console.print(f"Scraping top {scrape_top} results...\n")
                results = []
                async for result in engine.search_and_scrape(query, engines=engine_list, max_results=max_results, scrape_top=scrape_top, darkweb=darkweb, filter_llm=filter_llm):
                    status = "[green]OK[/green]" if result.success else "[red]FAIL[/red]"
                    console.print(f"  {status} {result.url}")
                    results.append({"url": result.url, "success": result.success, "content_preview": result.content[:200] if result.content else None})
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    console.print(f"\nSaved to: {output}")
            else:
                from deadman_scraper.discovery.aggregator import SearchAggregator
                aggregator = SearchAggregator(config)
                results = await aggregator.search(query, engines=engine_list, max_results=max_results, darkweb=darkweb)
                console.print(f"\n[green]Found {len(results)} results[/green]\n")
                table = Table(title="Search Results")
                table.add_column("Title", style="cyan")
                table.add_column("URL", style="blue")
                table.add_column("Engine")
                for r in results[:20]:
                    table.add_row(r.get("title", "")[:50], r.get("url", "")[:60], r.get("engine", ""))
                console.print(table)
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    console.print(f"\nSaved to: {output}")
    asyncio.run(_search())

@app.command()
def batch(
    urls_file: Path = typer.Argument(..., help="File with URLs"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
    format: str = typer.Option("json", "-f", "--format", help="Output format"),
    concurrency: int = typer.Option(5, "-c", "--concurrency", help="Concurrent requests"),
    tor: bool = typer.Option(False, "--tor", help="Force TOR routing"),
):
    """Batch scrape URLs from file."""
    if not urls_file.exists():
        console.print(f"[red]Error:[/red] File not found: {urls_file}")
        raise typer.Exit(1)
    urls = [line.strip() for line in urls_file.read_text().splitlines() if line.strip()]
    console.print(f"\n[cyan]Batch scraping {len(urls)} URLs[/cyan]\n")
    async def _batch():
        from deadman_scraper import Engine, Config
        config = Config.from_env()
        config.fetch.max_concurrent = concurrency
        results, success, failed = [], 0, 0
        async with Engine(config) as engine:
            async for result in engine.scrape_many(urls, meta={"force_tor": tor}):
                if result.success:
                    success += 1
                    stat = "[green]OK[/green]"
                else:
                    failed += 1
                    stat = "[red]FAIL[/red]"
                console.print(f"  {stat} {result.url}")
                results.append({"url": result.url, "success": result.success, "status_code": result.status_code, "error": result.error, "content_length": len(result.content) if result.content else 0})
        console.print(f"\n[green]Success: {success}[/green] | [red]Failed: {failed}[/red]")
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            console.print(f"Saved to: {output}")
    asyncio.run(_batch())

@app.command()
def tor(action: str = typer.Argument("status", help="Action: start/stop/restart/status")):
    """Manage TOR proxy."""
    async def _tor():
        from deadman_scraper.core.config import Config
        from deadman_scraper.fetch.tor_manager import TORManager
        config = Config.from_env()
        manager = TORManager(config.tor)
        if action == "start":
            console.print("[cyan]Starting TOR...[/cyan]")
            ok = await manager.start()
            if ok:
                ip = await manager.get_exit_ip()
                console.print(f"[green]TOR running![/green]")
                console.print(f"Proxy: {manager.proxy_url}")
                if ip:
                    console.print(f"Exit IP: {ip}")
            else:
                console.print("[red]Failed to start TOR[/red]")
                raise typer.Exit(1)
        elif action == "stop":
            console.print("[cyan]Stopping TOR...[/cyan]")
            await manager.stop()
            console.print("[green]TOR stopped[/green]")
        elif action == "restart":
            console.print("[cyan]Renewing TOR circuit...[/cyan]")
            ok = await manager.renew_circuit()
            if ok:
                ip = await manager.get_exit_ip()
                console.print(f"[green]New circuit established![/green]")
                if ip:
                    console.print(f"Exit IP: {ip}")
            else:
                console.print("[red]Failed to renew circuit[/red]")
        else:
            st = await manager.status()
            table = Table(title="TOR Status")
            table.add_column("Property", style="cyan")
            table.add_column("Value")
            table.add_row("Docker", "[green]Available[/green]" if st.docker_available else "[red]Not Found[/red]")
            table.add_row("Running", "[green]Yes[/green]" if st.running else "[red]No[/red]")
            if st.proxy_url:
                table.add_row("Proxy", st.proxy_url)
            if st.exit_ip:
                table.add_row("Exit IP", st.exit_ip)
            console.print(table)
    asyncio.run(_tor())

@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show/set/reset"),
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
):
    """Manage configuration."""
    from deadman_scraper.core.config import Config
    import yaml
    config_file = Path("config/default.yaml")
    if action == "show":
        cfg = Config.from_env()
        console.print(Panel(yaml.dump(cfg.model_dump(), default_flow_style=False), title="Configuration"))
    elif action == "set":
        if not key or not value:
            console.print("[red]Usage:[/red] deadman config set <key> <value>")
            raise typer.Exit(1)
        console.print(f"Setting {key} = {value}")
    elif action == "reset":
        console.print("[yellow]Resetting to defaults...[/yellow]")
        cfg = Config()
        cfg.to_yaml(config_file)
        console.print(f"[green]Reset complete![/green] Saved to {config_file}")

@app.command()
def stats():
    """Show LLM quota usage and statistics."""
    async def _stats():
        from deadman_scraper.core.config import Config
        from deadman_scraper.ai.llm_router import FreeLLMRouter
        cfg = Config.from_env()
        cfg.load_api_keys()
        router = FreeLLMRouter(cfg.llm, cfg.api_keys)
        st = router.get_quota_status()
        table = Table(title="LLM Provider Quotas")
        table.add_column("Provider", style="cyan")
        table.add_column("Used", justify="right")
        table.add_column("Remaining", justify="right")
        table.add_column("Limit", justify="right")
        table.add_column("Period")
        table.add_column("Usage", justify="right")
        for name, info in st.items():
            pct = info["percent_used"]
            pct_str = f"{pct:.1f}%"
            if pct > 90:
                pct_str = f"[red]{pct_str}[/red]"
            elif pct > 70:
                pct_str = f"[yellow]{pct_str}[/yellow]"
            else:
                pct_str = f"[green]{pct_str}[/green]"
            table.add_row(name.capitalize(), str(info["used"]), str(info["remaining"]), str(info["limit"]), info["period"], pct_str)
        console.print(table)
    asyncio.run(_stats())

def run():
    app()

if __name__ == "__main__":
    run()
