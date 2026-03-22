"""
Financial Advisor Agent — Main Entry Point

Usage:
  python main.py run-now              # Run pipeline once and send newsletter
  python main.py run-now --dry-run    # Run pipeline, print newsletter, do NOT send
  python main.py schedule             # Start scheduler (blocks), runs on configured schedule
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel

from src.analysis.etf_ranker import ETFRanker
from src.analysis.recommender import NewsletterGenerator
from src.analysis.signal_mapper import SignalMapper
from src.analysis.summarizer import NewsSummarizer
from src.delivery.email_delivery import EmailDelivery
from src.delivery.whatsapp_delivery import WhatsAppDelivery
from src.fetchers.geo_fetcher import GeopoliticalFetcher
from src.fetchers.market_fetcher import MarketDataFetcher
from src.fetchers.news_fetcher import NewsAggregator
from src.scheduler import build_scheduler
from src.utils.cache import Cache
from src.utils.config_loader import load_config
from src.utils.logger import logger

console = Console()


def run_pipeline(config, dry_run: bool = False) -> bool:
    """Execute the full analysis pipeline and optionally send the newsletter."""
    console.print(Panel("[bold blue]Financial Advisor Agent[/bold blue] — Starting pipeline", expand=False))
    cache = Cache(config.data.cache_dir)

    # ── Step 1: Fetch data in parallel ──────────────────────────────────────
    logger.info("Step 1: Fetching data...")

    # Load ETF tickers for market data
    import yaml
    from pathlib import Path
    with open(Path(config.data.etf_universe_file), encoding="utf-8") as f:
        universe = yaml.safe_load(f)
    etf_tickers = [etf["ticker_yahoo"] for etf in universe.get("etfs", []) if etf.get("pea_eligible")]

    news_fetcher = NewsAggregator(newsapi_key=config.newsapi_key or None)
    market_fetcher = MarketDataFetcher()
    geo_fetcher = GeopoliticalFetcher()

    articles, market_data, geo_events = None, None, None

    # Check cache first
    cached_articles = cache.get("articles")
    cached_market = cache.get("market_data")
    cached_geo = cache.get("geo_events")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        if cached_articles is None:
            futures["articles"] = executor.submit(
                news_fetcher.fetch,
                config.analysis.news_lookback_days,
                config.analysis.max_news_articles,
            )
        if cached_market is None:
            futures["market"] = executor.submit(market_fetcher.fetch, etf_tickers)
        if cached_geo is None:
            futures["geo"] = executor.submit(
                geo_fetcher.fetch,
                config.analysis.news_lookback_days,
            )

        for key, future in futures.items():
            try:
                result = future.result(timeout=60)
                if key == "articles":
                    articles = result
                    # Cache as dicts (dataclasses not JSON serializable directly)
                    cache.set("articles", [a.__dict__ for a in articles])
                elif key == "market":
                    market_data = result
                    # Market data is complex; skip caching (fast to re-fetch)
                elif key == "geo":
                    geo_events = result
                    cache.set("geo_events", [g.__dict__ for g in geo_events])
            except Exception as e:
                logger.error(f"Fetcher '{key}' failed: {e}")

    # Use cached data if available
    if articles is None and cached_articles:
        from src.fetchers.news_fetcher import Article
        articles = [Article(**a) for a in cached_articles]
    if market_data is None and cached_market:
        logger.warning("Using cached market data")
    if geo_events is None and cached_geo:
        from src.fetchers.geo_fetcher import GeoEvent
        geo_events = [GeoEvent(**g) for g in cached_geo]

    articles = articles or []
    geo_events = geo_events or []

    if market_data is None:
        logger.error("Market data fetch failed and no cache available. Aborting.")
        return False

    console.print(f"[green]✓[/green] Fetched {len(articles)} articles, {len(geo_events)} geo events")

    # ── Step 2: Claude Call 1 — Summarize & extract signals ─────────────────
    logger.info("Step 2: Summarizing news with Claude (Call 1)...")
    summarizer = NewsSummarizer(config.anthropic_api_key, config.analysis.claude_model)
    signal_set = summarizer.summarize(articles, geo_events, config.analysis.language)

    if not signal_set.signals:
        logger.warning("No signals extracted — check Claude response or input data")

    console.print(f"[green]✓[/green] Extracted {len(signal_set.signals)} macro signals")

    # ── Step 3: Map signals to ETF categories ────────────────────────────────
    logger.info("Step 3: Mapping signals to ETF categories...")
    mapper = SignalMapper(config.data.signal_map_file)
    category_scores = mapper.map(signal_set)

    # ── Step 4: Rank ETFs ────────────────────────────────────────────────────
    logger.info("Step 4: Ranking ETFs...")
    ranker = ETFRanker(config.data.etf_universe_file)
    candidates = ranker.rank(category_scores, market_data, config.analysis.top_etf_picks)

    console.print(f"[green]✓[/green] Top {len(candidates)} ETF candidates selected:")
    for c in candidates:
        console.print(f"  • {c.name} ({c.ticker_yahoo}) — score: {c.score:.2f}")

    # ── Step 5: Claude Call 2 — Generate newsletter ──────────────────────────
    logger.info("Step 5: Generating newsletter with Claude (Call 2)...")
    generator = NewsletterGenerator(config.anthropic_api_key, config.analysis.claude_model)
    newsletter = generator.generate(
        signal_set,
        candidates,
        market_data,
        language=config.analysis.language,
        frequency=config.schedule.frequency,
    )

    console.print(f"[green]✓[/green] Newsletter generated: '{newsletter.subject}'")

    if dry_run:
        console.print(Panel(
            newsletter.markdown_body,
            title="[bold yellow]DRY RUN — Newsletter Preview (not sent)[/bold yellow]",
            expand=True,
        ))
        return True

    # ── Step 6: Deliver ──────────────────────────────────────────────────────
    logger.info("Step 6: Delivering newsletter...")
    sent_any = False

    if config.delivery.email.enabled and config.email_recipients:
        email = EmailDelivery(
            provider=config.delivery.email.provider,
            gmail_user=config.gmail_user,
            gmail_app_password=config.gmail_app_password,
            sendgrid_api_key=config.sendgrid_api_key,
        )
        ok = email.send(newsletter, config.email_recipients)
        if ok:
            sent_any = True
            console.print(f"[green]✓[/green] Email sent to {config.email_recipients}")

    if config.delivery.whatsapp.enabled and config.whatsapp_recipients:
        wa = WhatsAppDelivery(
            account_sid=config.twilio_account_sid,
            auth_token=config.twilio_auth_token,
            from_number=config.twilio_whatsapp_from,
        )
        ok = wa.send(newsletter, config.whatsapp_recipients)
        if ok:
            sent_any = True
            console.print(f"[green]✓[/green] WhatsApp sent to {config.whatsapp_recipients}")

    if not sent_any:
        console.print("[yellow]⚠[/yellow]  No delivery channel sent the newsletter. Check config.")

    console.print(Panel("[bold green]Pipeline complete.[/bold green]", expand=False))
    return sent_any


def main():
    parser = argparse.ArgumentParser(
        description="Financial Advisor Agent — ETF newsletter generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run-now              # Run once and send
  python main.py run-now --dry-run    # Run once, print newsletter, don't send
  python main.py schedule             # Start scheduler (blocks)
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-now", help="Run the pipeline once")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print newsletter to console without sending",
    )
    run_parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml (default: config/settings.yaml)",
    )
    run_parser.add_argument(
        "--env",
        default=".env",
        help="Path to .env file (default: .env)",
    )

    sched_parser = subparsers.add_parser("schedule", help="Start the scheduler")
    sched_parser.add_argument("--config", default="config/settings.yaml")
    sched_parser.add_argument("--env", default=".env")

    args = parser.parse_args()

    # Load config (will raise with helpful message if required keys missing)
    try:
        config = load_config(settings_path=args.config, env_path=args.env)
    except ValueError as e:
        console.print(f"[bold red]Configuration error:[/bold red]\n{e}")
        console.print("\nCopy .env.example to .env and fill in your API keys.")
        sys.exit(1)

    if args.command == "run-now":
        success = run_pipeline(config, dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    elif args.command == "schedule":
        console.print(Panel(
            f"[bold blue]Scheduler starting[/bold blue]\n"
            f"Frequency: [yellow]{config.schedule.frequency}[/yellow] | "
            f"Time: [yellow]{config.schedule.time}[/yellow] | "
            f"Timezone: [yellow]{config.schedule.timezone}[/yellow]\n\n"
            f"Press Ctrl+C to stop.",
            expand=False,
        ))
        scheduler = build_scheduler(config, lambda: run_pipeline(config))
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
