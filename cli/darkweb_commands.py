"""Dark Web CLI commands.

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def register_darkweb_commands(app: typer.Typer):
    """Register dark web commands with the CLI app."""

    @app.command()
    def darkweb_search(
        query: str = typer.Argument(..., help="Search query"),
        engines: Optional[str] = typer.Option(
            None, "--engines", "-e",
            help="Comma-separated engines (ahmia,torch,haystack,darksearch,etc)"
        ),
        max_results: int = typer.Option(50, "-n", "--max", help="Max results"),
        scrape: bool = typer.Option(False, "--scrape", help="Scrape result pages"),
        output: Path = typer.Option(
            Path("data/darkweb_results"), "-o", "--output",
            help="Output directory"
        ),
    ):
        """Search dark web using 14+ search engines (Darker-style meta-search)."""
        async def _search():
            from deadman_scraper import Config
            from deadman_scraper.darkweb import DarkWebEngine, DarkWebConfig

            config = Config.from_env()
            config.load_api_keys()

            # Parse engines
            engine_list = None
            if engines:
                engine_list = [e.strip() for e in engines.split(",")]

            dwconfig = DarkWebConfig(
                search_engines=engine_list or ["ahmia", "torch", "haystack", "darksearch"],
                search_max_results=max_results,
                output_path=str(output),
            )

            console.print(Panel(
                f"[cyan]Query:[/cyan] {query}\n"
                f"[cyan]Engines:[/cyan] {engine_list or 'default (4)'}\n"
                f"[cyan]Max Results:[/cyan] {max_results}\n"
                f"[cyan]Scrape Results:[/cyan] {'Yes' if scrape else 'No'}",
                title="Dark Web Search"
            ))

            engine = DarkWebEngine(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=dwconfig,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Searching dark web...", total=None)
                result = await engine.search(query, scrape_results=scrape)

            # Display results
            table = Table(title=f"Dark Web Search: {query}")
            table.add_column("URL", style="blue", max_width=60)
            table.add_column("Title", max_width=40)
            table.add_column("Engine", style="cyan")

            for sr in result.search_results[:20]:
                url = sr.url if hasattr(sr, 'url') else str(sr)
                title = (sr.title[:37] + "...") if hasattr(sr, 'title') and len(sr.title) > 40 else (sr.title if hasattr(sr, 'title') else "")
                eng = sr.engine if hasattr(sr, 'engine') else ""
                table.add_row(url[:57] + "..." if len(url) > 60 else url, title, eng)

            console.print(table)
            console.print(f"\n[green]Total results:[/green] {len(result.search_results)}")
            console.print(f"[green]Duration:[/green] {result.duration_seconds:.1f}s")

            if result.errors:
                console.print(f"[yellow]Errors:[/yellow] {len(result.errors)}")

        asyncio.run(_search())

    @app.command()
    def darkweb_crawl(
        url: str = typer.Argument(..., help="Seed .onion URL to crawl"),
        max_depth: int = typer.Option(2, "-d", "--depth", help="Maximum crawl depth"),
        max_pages: int = typer.Option(100, "-n", "--max-pages", help="Maximum pages"),
        delay: float = typer.Option(1.0, "--delay", help="Delay between requests"),
        extract_media: bool = typer.Option(True, "--media/--no-media", help="Extract media"),
        output: Path = typer.Option(
            Path("data/darkweb_crawl"), "-o", "--output",
            help="Output directory"
        ),
    ):
        """Crawl an .onion site with depth control (TorCrawl-style)."""
        async def _crawl():
            from deadman_scraper import Config
            from deadman_scraper.darkweb import DarkWebEngine, DarkWebConfig

            config = Config.from_env()
            config.load_api_keys()

            dwconfig = DarkWebConfig(
                crawl_max_depth=max_depth,
                crawl_max_pages=max_pages,
                crawl_delay=delay,
                extract_media=extract_media,
                output_path=str(output),
            )

            console.print(Panel(
                f"[cyan]Seed URL:[/cyan] {url}\n"
                f"[cyan]Max Depth:[/cyan] {max_depth}\n"
                f"[cyan]Max Pages:[/cyan] {max_pages}\n"
                f"[cyan]Delay:[/cyan] {delay}s\n"
                f"[cyan]Extract Media:[/cyan] {'Yes' if extract_media else 'No'}",
                title="Dark Web Crawl"
            ))

            engine = DarkWebEngine(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=dwconfig,
            )

            def progress_callback(crawl_result):
                console.print(f"  [dim]Crawled:[/dim] {crawl_result.url[:60]}...")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Crawling...", total=None)
                result = await engine.crawl(url, callback=progress_callback)

            # Display stats
            table = Table(title="Crawl Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")

            table.add_row("Pages Crawled", str(len(result.crawl_results)))
            table.add_row("Media Items", str(len(result.media_items)))
            table.add_row("Duration", f"{result.duration_seconds:.1f}s")

            if result.crawl_stats:
                for key, val in result.crawl_stats.items():
                    if isinstance(val, (int, float, str)):
                        table.add_row(key.replace("_", " ").title(), str(val))

            console.print(table)

            if result.errors:
                console.print(f"\n[yellow]Errors:[/yellow] {len(result.errors)}")
            console.print(f"\n[green]Results saved to:[/green] {output}")

        asyncio.run(_crawl())

    @app.command()
    def darkweb_osint(
        target: str = typer.Argument(..., help="Target (email, domain, bitcoin, username, or URL)"),
        search: bool = typer.Option(True, "--search/--no-search", help="Search dark web for target"),
        output: Path = typer.Option(
            Path("data/darkweb_osint"), "-o", "--output",
            help="Output directory"
        ),
    ):
        """Collect OSINT from dark web (SpiderFoot-style)."""
        async def _osint():
            from deadman_scraper import Config
            from deadman_scraper.darkweb import DarkWebEngine, DarkWebConfig

            config = Config.from_env()
            config.load_api_keys()

            dwconfig = DarkWebConfig(
                output_path=str(output),
            )

            console.print(Panel(
                f"[cyan]Target:[/cyan] {target}\n"
                f"[cyan]Search Dark Web:[/cyan] {'Yes' if search else 'No'}",
                title="Dark Web OSINT"
            ))

            engine = DarkWebEngine(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=dwconfig,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Collecting OSINT...", total=None)
                result = await engine.collect_osint(target, search_dark_web=search)

            # Display entities by type
            console.print(f"\n[green]Found {len(result.osint_entities)} OSINT entities[/green]\n")

            if result.osint_stats.get("by_type"):
                type_table = Table(title="Entities by Type")
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", justify="right")

                for entity_type, count in result.osint_stats["by_type"].items():
                    type_table.add_row(entity_type, str(count))
                console.print(type_table)

            # Show sample entities
            if result.osint_entities:
                sample_table = Table(title="Sample Entities (first 10)")
                sample_table.add_column("Type", style="cyan")
                sample_table.add_column("Value", style="yellow", max_width=50)
                sample_table.add_column("Source", style="dim", max_width=40)

                for entity in result.osint_entities[:10]:
                    sample_table.add_row(
                        entity.entity_type,
                        entity.value[:47] + "..." if len(entity.value) > 50 else entity.value,
                        entity.source_url[:37] + "..." if len(entity.source_url) > 40 else entity.source_url
                    )
                console.print(sample_table)

            console.print(f"\n[green]Duration:[/green] {result.duration_seconds:.1f}s")
            console.print(f"[green]Results saved to:[/green] {output}")

        asyncio.run(_osint())

    @app.command()
    def darkweb_validate(
        urls_file: Path = typer.Argument(..., help="File with .onion URLs (one per line)"),
        detect_clones: bool = typer.Option(True, "--clones/--no-clones", help="Detect clone sites"),
        output: Path = typer.Option(
            Path("data/darkweb_validation.json"), "-o", "--output",
            help="Output file"
        ),
        concurrency: int = typer.Option(5, "-c", "--concurrency", help="Concurrent validations"),
    ):
        """Validate .onion URLs and detect clones (Fresh Onions-style)."""
        async def _validate():
            import json
            from deadman_scraper import Config
            from deadman_scraper.darkweb import DarkWebEngine, DarkWebConfig

            config = Config.from_env()
            config.load_api_keys()

            # Load URLs
            if not urls_file.exists():
                console.print(f"[red]Error:[/red] File not found: {urls_file}")
                raise typer.Exit(1)

            urls = [
                line.strip() for line in urls_file.read_text().splitlines()
                if line.strip() and ".onion" in line
            ]

            if not urls:
                console.print("[red]No .onion URLs found in file[/red]")
                raise typer.Exit(1)

            console.print(Panel(
                f"[cyan]URLs to validate:[/cyan] {len(urls)}\n"
                f"[cyan]Detect Clones:[/cyan] {'Yes' if detect_clones else 'No'}\n"
                f"[cyan]Concurrency:[/cyan] {concurrency}",
                title="Onion Validation"
            ))

            dwconfig = DarkWebConfig(
                detect_clones=detect_clones,
                max_concurrent=concurrency,
            )

            engine = DarkWebEngine(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=dwconfig,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(f"Validating {len(urls)} onions...", total=None)
                result = await engine.validate_onions(urls)

            # Display results
            alive = [s for s in result.validation_results if s.is_alive]
            dead = [s for s in result.validation_results if not s.is_alive]

            table = Table(title="Validation Results")
            table.add_column("URL", style="blue", max_width=50)
            table.add_column("Status", justify="center")
            table.add_column("Response", justify="right")
            table.add_column("Services", max_width=30)

            for status in result.validation_results[:20]:
                url_short = status.url[:47] + "..." if len(status.url) > 50 else status.url
                state = "[green]UP[/green]" if status.is_alive else "[red]DOWN[/red]"
                response = f"{status.response_time_ms:.0f}ms" if status.is_alive else "-"
                services = ", ".join(status.detected_services[:3]) if status.detected_services else "-"
                table.add_row(url_short, state, response, services)

            console.print(table)

            console.print(f"\n[green]Alive:[/green] {len(alive)}")
            console.print(f"[red]Dead:[/red] {len(dead)}")

            if result.clone_detections:
                console.print(f"\n[yellow]Detected {len(result.clone_detections)} potential clones:[/yellow]")
                for clone in result.clone_detections[:5]:
                    console.print(f"  {clone['url']} -> clone of {clone['clone_of']} ({clone['similarity']:.0%})")

            # Save results
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({
                "alive": [s.to_dict() for s in alive],
                "dead": [s.to_dict() for s in dead],
                "clones": result.clone_detections,
                "duration_seconds": result.duration_seconds,
            }, indent=2))

            console.print(f"\n[green]Results saved to:[/green] {output}")

        asyncio.run(_validate())

    @app.command()
    def darkweb_investigate(
        target: str = typer.Argument(..., help="Target URL or search query"),
        crawl_depth: int = typer.Option(1, "-d", "--depth", help="Crawl depth for discovered sites"),
        max_pages: int = typer.Option(20, "-n", "--max-pages", help="Max pages per site"),
        output: Path = typer.Option(
            Path("data/darkweb_investigation"), "-o", "--output",
            help="Output directory"
        ),
    ):
        """Full dark web investigation (search + validate + crawl + OSINT)."""
        async def _investigate():
            from deadman_scraper import Config
            from deadman_scraper.darkweb import DarkWebEngine, DarkWebConfig

            config = Config.from_env()
            config.load_api_keys()

            console.print(Panel(
                f"[cyan]Target:[/cyan] {target}\n"
                f"[cyan]Crawl Depth:[/cyan] {crawl_depth}\n"
                f"[cyan]Max Pages:[/cyan] {max_pages}\n"
                f"[cyan]Output:[/cyan] {output}\n\n"
                "[dim]This will:[/dim]\n"
                "  1. Search dark web for target\n"
                "  2. Validate discovered .onion URLs\n"
                "  3. Crawl alive sites\n"
                "  4. Extract OSINT from all content",
                title="Full Dark Web Investigation"
            ))

            dwconfig = DarkWebConfig(
                crawl_max_depth=crawl_depth,
                crawl_max_pages=max_pages,
                output_path=str(output),
            )

            engine = DarkWebEngine(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=dwconfig,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Running full investigation...", total=None)
                result = await engine.full_investigation(
                    target,
                    crawl_depth=crawl_depth,
                    max_pages=max_pages,
                )

            # Display comprehensive results
            console.print("\n[bold green]Investigation Complete![/bold green]\n")

            summary = Table(title="Investigation Summary")
            summary.add_column("Category", style="cyan")
            summary.add_column("Count", justify="right")

            summary.add_row("Search Results", str(len(result.search_results)))
            summary.add_row("Sites Validated", str(len(result.validation_results)))
            summary.add_row("Clone Detections", str(len(result.clone_detections)))
            summary.add_row("Pages Crawled", str(len(result.crawl_results)))
            summary.add_row("Media Items", str(len(result.media_items)))
            summary.add_row("OSINT Entities", str(len(result.osint_entities)))

            console.print(summary)

            if result.osint_stats.get("by_type"):
                osint_table = Table(title="OSINT Breakdown")
                osint_table.add_column("Entity Type", style="yellow")
                osint_table.add_column("Count", justify="right")
                for etype, count in result.osint_stats["by_type"].items():
                    osint_table.add_row(etype, str(count))
                console.print(osint_table)

            console.print(f"\n[green]Duration:[/green] {result.duration_seconds:.1f}s")
            console.print(f"[green]Results saved to:[/green] {output}")

            if result.errors:
                console.print(f"[yellow]Errors encountered:[/yellow] {len(result.errors)}")

        asyncio.run(_investigate())

    @app.command()
    def darkweb_media(
        url: str = typer.Argument(..., help=".onion URL to extract media from"),
        download: bool = typer.Option(False, "--download", help="Download media files"),
        detect_faces: bool = typer.Option(False, "--faces", help="Detect faces in images"),
        output: Path = typer.Option(
            Path("data/darkweb_media"), "-o", "--output",
            help="Output directory"
        ),
    ):
        """Extract media from .onion page (DarkScrape-style)."""
        async def _media():
            from deadman_scraper import Config
            from deadman_scraper.darkweb.media import MediaExtractor, ExtractionConfig

            config = Config.from_env()
            config.load_api_keys()

            console.print(Panel(
                f"[cyan]URL:[/cyan] {url}\n"
                f"[cyan]Download:[/cyan] {'Yes' if download else 'No'}\n"
                f"[cyan]Face Detection:[/cyan] {'Yes' if detect_faces else 'No'}",
                title="Dark Web Media Extraction"
            ))

            media_config = ExtractionConfig(
                download_media=download,
                download_path=str(output),
                detect_faces=detect_faces,
            )

            extractor = MediaExtractor(
                tor_manager=config.get_tor_manager() if hasattr(config, 'get_tor_manager') else None,
                config=media_config,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Extracting media...", total=None)
                items = await extractor.extract_from_url(url)

            # Display results
            table = Table(title=f"Media from {url[:50]}...")
            table.add_column("Type", style="cyan")
            table.add_column("URL", max_width=50)
            table.add_column("Size", justify="right")

            for item in items[:20]:
                size = f"{item.file_size / 1024:.1f}KB" if item.file_size else "-"
                table.add_row(item.media_type, item.url[:47] + "..." if len(item.url) > 50 else item.url, size)

            console.print(table)

            # Summary by type
            by_type = {}
            for item in items:
                by_type[item.media_type] = by_type.get(item.media_type, 0) + 1

            console.print(f"\n[green]Total media items:[/green] {len(items)}")
            for mtype, count in by_type.items():
                console.print(f"  {mtype}: {count}")

            if download:
                downloaded = [i for i in items if i.downloaded]
                console.print(f"\n[green]Downloaded:[/green] {len(downloaded)} files to {output}")

        asyncio.run(_media())
