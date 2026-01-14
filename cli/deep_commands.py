"""Deep scraping CLI commands."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def register_deep_commands(app: typer.Typer):
    """Register deep scraping commands with the CLI app."""

    @app.command()
    def deep(
        urls_file: Path = typer.Argument(..., help="File with seed URLs"),
        output: Path = typer.Option(Path("data/deep_results"), "-o", "--output", help="Output directory"),
        max_depth: int = typer.Option(5, "--max-depth", "-d", help="Maximum link depth to follow"),
        max_pages: int = typer.Option(1000, "--max-pages", "-n", help="Maximum pages to scrape"),
        concurrency: int = typer.Option(5, "-c", "--concurrency", help="Concurrent scrapers"),
        tor: bool = typer.Option(False, "--tor", help="Use TOR for all requests"),
        allow_domains: Optional[str] = typer.Option(None, "--allow-domains", help="Comma-separated allowed domains"),
        block_domains: Optional[str] = typer.Option(None, "--block-domains", help="Comma-separated blocked domains"),
        resume: bool = typer.Option(False, "--resume", help="Resume from existing queue"),
        save_content: bool = typer.Option(True, "--save-content/--no-save-content", help="Save scraped content"),
    ):
        """Recursive deep-scrape from seed URLs until exhaustion."""
        async def _deep():
            from deadman_scraper import Engine, Config
            from deadman_scraper.core.recursive import RecursiveScraper

            config = Config.from_env()
            config.load_api_keys()

            # Load seed URLs
            if resume:
                seeds = []
                console.print("[yellow]Resuming from existing queue...[/yellow]")
            else:
                if not urls_file.exists():
                    console.print(f"[red]Error:[/red] File not found: {urls_file}")
                    raise typer.Exit(1)
                seeds = [l.strip() for l in urls_file.read_text().splitlines() if l.strip() and not l.startswith('#')]

            console.print(Panel(
                f"[cyan]Seeds:[/cyan] {len(seeds)}\n"
                f"[cyan]Max depth:[/cyan] {max_depth}\n"
                f"[cyan]Max pages:[/cyan] {max_pages}\n"
                f"[cyan]Concurrency:[/cyan] {concurrency}\n"
                f"[cyan]TOR:[/cyan] {'Yes' if tor else 'No'}\n"
                f"[cyan]Output:[/cyan] {output}",
                title="Deep Scrape Configuration"
            ))

            db_path = output / "queue.db"
            scraper = RecursiveScraper(config, db_path=str(db_path), output_dir=str(output))

            # Set domain filters
            if allow_domains:
                allowed = [d.strip() for d in allow_domains.split(',')]
                scraper.set_domain_filter(allowed=allowed)
            if block_domains:
                blocked = [d.strip() for d in block_domains.split(',')]
                scraper.set_domain_filter(blocked=blocked)

            console.print("\n[cyan]Starting deep scrape...[/cyan]\n")

            stats = await scraper.run(
                seed_urls=seeds,
                max_depth=max_depth,
                max_pages=max_pages,
                concurrency=concurrency,
                use_tor=tor,
                save_content=save_content
            )

            # Display results
            table = Table(title="Deep Scrape Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")

            table.add_row("Total Scraped", str(stats.total_scraped))
            table.add_row("Successful", f"[green]{stats.total_success}[/green]")
            table.add_row("Failed", f"[red]{stats.total_failed}[/red]")
            table.add_row("URLs Found", str(stats.total_urls_found))
            table.add_row("URLs Added", str(stats.total_urls_added))
            duration = stats.to_dict()['duration_seconds']
            table.add_row("Duration", f"{duration:.1f}s")

            console.print("\n")
            console.print(table)

            # Show top domains
            if stats.by_domain:
                domain_table = Table(title="Top Domains")
                domain_table.add_column("Domain", style="blue")
                domain_table.add_column("Count", justify="right")
                for domain, count in sorted(stats.by_domain.items(), key=lambda x: -x[1])[:10]:
                    domain_table.add_row(domain, str(count))
                console.print(domain_table)

            console.print(f"\n[green]Results saved to:[/green] {output}")

        asyncio.run(_deep())

    @app.command()
    def deep_search(
        query: str = typer.Argument(..., help="Search query"),
        engines: Optional[str] = typer.Option(None, "--engines", help="Search engines"),
        max_results: int = typer.Option(20, "-n", "--max", help="Max search results"),
        max_depth: int = typer.Option(3, "--max-depth", "-d", help="Max scrape depth"),
        max_pages: int = typer.Option(500, "--max-pages", help="Max pages to scrape"),
        output: Path = typer.Option(Path("data/deep_results"), "-o", "--output", help="Output directory"),
        tor: bool = typer.Option(False, "--tor", help="Use TOR"),
        darkweb: bool = typer.Option(False, "--darkweb", help="Include dark web engines"),
    ):
        """Search and then recursively scrape results."""
        async def _deep_search():
            from deadman_scraper import Engine, Config
            from deadman_scraper.discovery.aggregator import SearchAggregator
            from deadman_scraper.core.recursive import RecursiveScraper

            config = Config.from_env()
            config.load_api_keys()

            # First, search
            console.print(f"\n[cyan]Searching:[/cyan] {query}")
            engine_list = engines.split(",") if engines else None

            aggregator = SearchAggregator(config)
            results = await aggregator.search(
                query,
                engines=engine_list,
                max_results=max_results,
                darkweb=darkweb
            )

            console.print(f"[green]Found {len(results)} search results[/green]")

            # Extract seed URLs
            seeds = [r.get('url') for r in results if r.get('url')]
            if not seeds:
                console.print("[red]No URLs found from search[/red]")
                raise typer.Exit(1)

            console.print(f"\n[cyan]Starting deep scrape of {len(seeds)} URLs...[/cyan]\n")

            # Deep scrape
            db_path = output / "queue.db"
            scraper = RecursiveScraper(config, db_path=str(db_path), output_dir=str(output))

            stats = await scraper.run(
                seed_urls=seeds,
                max_depth=max_depth,
                max_pages=max_pages,
                use_tor=tor
            )

            console.print(f"\n[green]Deep scrape complete![/green]")
            console.print(f"  Total scraped: {stats.total_scraped}")
            console.print(f"  URLs discovered: {stats.total_urls_found}")
            console.print(f"  Results saved to: {output}")

        asyncio.run(_deep_search())

    @app.command()
    def queue_status(
        db_path: Path = typer.Option(Path("data/deep_results/queue.db"), "--db", help="Queue database path"),
    ):
        """Show status of the scrape queue."""
        from deadman_scraper.core.persistent_queue import PersistentQueue

        if not db_path.exists():
            console.print(f"[red]Queue not found:[/red] {db_path}")
            raise typer.Exit(1)

        queue = PersistentQueue(str(db_path))
        stats = queue.get_stats()

        # Queue stats
        table = Table(title="Queue Status")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right")

        q = stats['queue']
        table.add_row("Total", str(q['total']))
        table.add_row("Pending", f"[yellow]{q['pending']}[/yellow]")
        table.add_row("In Progress", f"[blue]{q['in_progress']}[/blue]")
        table.add_row("Completed", f"[green]{q['completed']}[/green]")
        table.add_row("Failed", f"[red]{q['failed']}[/red]")

        console.print(table)

        # Depth distribution
        if stats['depth_distribution']:
            depth_table = Table(title="Depth Distribution")
            depth_table.add_column("Depth", style="cyan")
            depth_table.add_column("URLs", justify="right")
            for depth, count in sorted(stats['depth_distribution'].items()):
                depth_table.add_row(str(depth), str(count))
            console.print(depth_table)

        # Top domains
        if stats['top_domains']:
            domain_table = Table(title="Top Domains")
            domain_table.add_column("Domain", style="blue")
            domain_table.add_column("URLs", justify="right")
            for domain, count in stats['top_domains'].items():
                domain_table.add_row(domain, str(count))
            console.print(domain_table)

    @app.command()
    def extract_urls(
        content_dir: Path = typer.Argument(Path("data/deep_results/content"), help="Content directory"),
        output: Path = typer.Option(Path("data/extracted_urls.txt"), "-o", "--output", help="Output file"),
    ):
        """Extract all URLs from scraped content files."""
        import json

        if not content_dir.exists():
            console.print(f"[red]Directory not found:[/red] {content_dir}")
            raise typer.Exit(1)

        all_urls = set()

        for json_file in content_dir.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    urls = data.get('extracted_urls', [])
                    all_urls.update(urls)
            except Exception:
                continue

        # Write to file
        with open(output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(all_urls)))

        console.print(f"[green]Extracted {len(all_urls)} unique URLs[/green]")
        console.print(f"Saved to: {output}")
