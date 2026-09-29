#!/usr/bin/env python3
"""BioCatalyst CLI - Autonomous Clinical Trial & Financial Intelligence Engine.

Usage:
  python cli.py scan [--condition CONDITION] [--sponsor SPONSOR] [--query QUERY] [--limit N]
  python cli.py financials [TICKER]
  python cli.py audit NCT_ID [--export-md]
  python cli.py watchlist [list|add|remove] [IDENTIFIER]
  python cli.py export-csv [OUTPUT_PATH]
  python cli.py serve
"""

import sys
import os

# Ensure UTF-8 output on Windows consoles to prevent cp1252 charmap errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.db import DatabaseManager
from core.models import ClinicalTrial, CompanyFinancials
from clients.clinical_trials import ClinicalTrialsClient
from clients.market_data import MarketDataClient
from clients.sponsor_matcher import SponsorMatcher
from agents.committee import DiligenceCommittee
from reports.exporter import ReportExporter

console = Console(highlight=False)


def handle_scan(args, db: DatabaseManager, ct_client: ClinicalTrialsClient):
    console.print(f"[bold cyan][SCAN] Scanning ClinicalTrials.gov v2 API...[/bold cyan]")
    if args.sponsor:
        console.print(f"  * Sponsor Filter: [yellow]{args.sponsor}[/yellow]")
    if args.condition:
        console.print(f"  * Condition Filter: [yellow]{args.condition}[/yellow]")
    if args.query:
        console.print(f"  * Search Query: [yellow]{args.query}[/yellow]")

    trials = ct_client.search_trials(
        query=args.query,
        condition=args.condition,
        sponsor=args.sponsor,
        page_size=args.limit
    )

    if not trials:
        console.print("[red]No trials matching criteria were found.[/red]")
        return

    # Upsert into database
    for t in trials:
        db.upsert_trial(t)

    table = Table(title=f"Clinical Trial Scan Results ({len(trials)} studies)")
    table.add_column("NCT ID", style="cyan", no_wrap=True)
    table.add_column("Sponsor", style="white")
    table.add_column("Ticker", style="bold green", no_wrap=True)
    table.add_column("Phase", style="magenta")
    table.add_column("Catalyst Window", style="bold yellow")
    table.add_column("Status", style="blue")
    table.add_column("Primary Indication", style="dim")

    for t in trials:
        ticker_display = t.matched_ticker or "-"
        table.add_row(
            t.nct_id,
            t.sponsor_name[:24],
            ticker_display,
            ", ".join(t.phases) or "N/A",
            t.estimated_catalyst_window or "TBD",
            t.status[:16],
            (t.conditions[0][:28] if t.conditions else "N/A")
        )

    console.print(table)
    console.print(f"[green]+ Saved {len(trials)} trials into local SQLite database.[/green]")


def handle_financials(args, db: DatabaseManager, mkt_client: MarketDataClient):
    tickers = []
    if args.ticker:
        tickers = [args.ticker.strip().upper()]
    else:
        # Pull distinct tickers from trials or watchlist
        trials = db.list_trials(limit=500)
        found_tickers = {t.matched_ticker for t in trials if t.matched_ticker}
        watchlist = db.get_watchlist()
        for item in watchlist:
            if item["item_type"] == "TICKER":
                found_tickers.add(item["identifier"])
        tickers = sorted(list(found_tickers))
        if not tickers:
            tickers = ["MRNA", "BNTX", "VKTX", "CRSP", "ALNY", "VRTX"]

    console.print(f"[bold cyan][FINANCIALS] Auditing Financial Solvency & Runway for {len(tickers)} Tickers...[/bold cyan]")

    table = Table(title="Biotech Balance Sheet & Dilution Risk Radar")
    table.add_column("Ticker", style="bold cyan", no_wrap=True)
    table.add_column("Company", style="white")
    table.add_column("Price", style="green")
    table.add_column("Market Cap", style="white")
    table.add_column("Liquid Cash", style="bold green")
    table.add_column("Qtr Burn", style="red")
    table.add_column("Runway (Mos)", style="bold yellow")
    table.add_column("Dilution Risk", style="bold")

    for ticker in tickers:
        fin = mkt_client.get_financials(ticker)
        if not fin:
            table.add_row(ticker, "Error / Data Unavailable", "-", "-", "-", "-", "-", "[dim]UNKNOWN[/dim]")
            continue

        db.upsert_financials(fin)

        risk_color = {
            "LOW": "[green]LOW[/green]",
            "MODERATE": "[yellow]MODERATE[/yellow]",
            "HIGH": "[bold red]HIGH[/bold red]",
            "CRITICAL": "[bold white on red]CRITICAL[/bold white on red]"
        }.get(fin.dilution_risk_level.value, fin.dilution_risk_level.value)

        runway_display = f"{fin.cash_runway_months:.1f}" if fin.cash_runway_months and fin.cash_runway_months < 900 else (
            "Indefinite" if fin.cash_runway_months else "N/A"
        )
        price_display = f"${fin.stock_price:.2f}" if fin.stock_price else "-"
        mcap_display = f"${fin.market_cap / 1e9:.2f}B" if fin.market_cap and fin.market_cap >= 1e9 else (
            f"${fin.market_cap / 1e6:.1f}M" if fin.market_cap else "-"
        )
        cash_display = f"${fin.total_liquid_cash / 1e9:.2f}B" if fin.total_liquid_cash and fin.total_liquid_cash >= 1e9 else (
            f"${fin.total_liquid_cash / 1e6:.1f}M" if fin.total_liquid_cash else "-"
        )
        burn_display = f"${fin.quarterly_burn_rate / 1e6:.1f}M" if fin.quarterly_burn_rate else "$0.0M"

        table.add_row(
            fin.ticker,
            fin.company_name[:22],
            price_display,
            mcap_display,
            cash_display,
            burn_display,
            runway_display,
            risk_color
        )

    console.print(table)
    console.print(f"[green]+ Financial records cached to local SQLite database.[/green]")


def handle_audit(args, db: DatabaseManager, ct_client: ClinicalTrialsClient, mkt_client: MarketDataClient):
    nct_id = args.nct_id.strip().upper()
    console.print(f"[bold cyan][AUDIT] Convening AI Diligence Committee for {nct_id}...[/bold cyan]")

    # 1. Fetch Trial
    trial = db.get_trial(nct_id)
    if not trial:
        console.print(f"  * Trial not in local DB, fetching live from ClinicalTrials.gov...")
        trial = ct_client.fetch_trial_by_nct(nct_id)
        if not trial:
            console.print(f"[red]Error: Could not retrieve trial protocol for {nct_id}.[/red]")
            return
        db.upsert_trial(trial)

    console.print(f"  * Asset: [bold]{trial.title}[/bold]")
    console.print(f"  * Sponsor: [yellow]{trial.sponsor_name}[/yellow] (Ticker: {trial.matched_ticker or 'None'})")

    # 2. Fetch Financials if public sponsor
    financials = None
    if trial.matched_ticker:
        financials = db.get_financials(trial.matched_ticker)
        if not financials:
            console.print(f"  * Fetching balance sheet data for ${trial.matched_ticker}...")
            financials = mkt_client.get_financials(trial.matched_ticker)
            if financials:
                db.upsert_financials(financials)

    # 3. Convene Committee
    committee = DiligenceCommittee()
    console.print("  * Agent 1: Dr. Elena Vance analyzing molecular target plausibility...")
    console.print("  * Agent 2: Dr. Marcus Thorne critiquing trial statistical rigor & endpoints...")
    console.print("  * Agent 3: Alexander Vance, CFA assessing cash runway vs readout alignment...")

    report = committee.conduct_diligence(trial, financials, include_pubmed=True)
    report_id = db.save_report(report)

    # Render Terminal Output
    verdict_styles = {
        "STRONG_CONVICTION": "bold green",
        "SPECULATIVE_ASYMMETRIC": "bold yellow",
        "NEUTRAL_WATCH": "bold blue",
        "HIGH_RISK_AVOID": "bold white on red"
    }
    verdict_style = verdict_styles.get(report.consensus_verdict.value, "bold white")

    summary_panel = Panel(
        f"[bold]Consensus Verdict:[/bold] [{verdict_style}]{report.consensus_verdict.value}[/{verdict_style}]\n"
        f"[bold]Overall Diligence Score:[/bold] [bold cyan]{report.overall_score:.1f} / 100[/bold cyan]\n"
        f"[bold]Target Readout Window:[/bold] [bold yellow]{trial.estimated_catalyst_window or 'TBD'}[/bold yellow]\n\n"
        f"{report.executive_summary}",
        title=f"AI Diligence Consensus: {report.nct_id}",
        border_style="cyan"
    )
    console.print(summary_panel)

    # Detailed agent summary
    console.print("\n[bold underline]1. Molecular Biology Audit:[/bold underline]")
    console.print(f"  * Target: [cyan]{report.molecular_analysis.target_name}[/cyan]")
    console.print(f"  * Modality: [magenta]{report.molecular_analysis.modality}[/magenta]")
    console.print(f"  * Plausibility: [green]{report.molecular_analysis.biological_plausibility}[/green]")
    console.print(f"  * Target Validation: {report.molecular_analysis.target_validation_summary}")

    console.print("\n[bold underline]2. Biostatistical Audit:[/bold underline]")
    console.print(f"  * Design Rigor: [yellow]{report.biostat_audit.trial_design_rigor}[/yellow]")
    console.print(f"  * Endpoint Quality: [cyan]{report.biostat_audit.endpoint_quality}[/cyan]")
    console.print(f"  * Endpoints: {report.biostat_audit.endpoint_analysis}")
    if report.biostat_audit.red_flags:
        for rf in report.biostat_audit.red_flags:
            console.print(f"  * [red][WARNING] Red Flag:[/red] {rf}")

    console.print("\n[bold underline]3. Bio-Financial Asymmetry Audit:[/bold underline]")
    console.print(f"  * Runway Alignment: [yellow]{report.financial_audit.runway_vs_readout_alignment}[/yellow]")
    console.print(f"  * Binary Exposure: [cyan]{report.financial_audit.binary_risk_exposure}[/cyan]")
    console.print(f"  * Dilution Window: {report.financial_audit.projected_dilution_window}")

    # Export markdown dossier if requested
    if args.export_md:
        out_path = Path(f"reports/{nct_id}_dossier.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_text = ReportExporter.export_to_markdown(report, trial, financials)
        out_path.write_text(md_text, encoding="utf-8")
        console.print(f"\n[green]+ Dossier exported to: [bold]{out_path}[/bold][/green]")


def handle_watchlist(args, db: DatabaseManager):
    action = (args.action or "list").lower()
    if action == "list":
        wl = db.get_watchlist()
        if not wl:
            console.print("[dim]Watchlist is empty. Add with `python cli.py watchlist add IDENTIFIER`[/dim]")
            return
        table = Table(title="Catalyst Watchlist")
        table.add_column("Identifier", style="bold cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Alias / Label", style="white")
        table.add_column("Notes", style="dim")
        table.add_column("Added Date", style="blue")
        for item in wl:
            table.add_row(item["identifier"], item["item_type"], item["alias"] or "-", item["notes"] or "-", item["added_at"][:10])
        console.print(table)
    elif action == "add":
        ident = (args.identifier or "").strip().upper()
        if not ident:
            console.print("[red]Please specify an identifier (e.g., MRNA or NCT03897881).[/red]")
            return
        itype = "NCT" if ident.startswith("NCT") else "TICKER"
        db.add_to_watchlist(ident, itype, alias=args.alias, notes=args.notes or "")
        console.print(f"[green]+ Added {ident} ({itype}) to Watchlist.[/green]")
    elif action == "remove":
        ident = (args.identifier or "").strip().upper()
        if db.remove_from_watchlist(ident):
            console.print(f"[green]+ Removed {ident} from Watchlist.[/green]")
        else:
            console.print(f"[yellow]Identifier {ident} not found in Watchlist.[/yellow]")


def handle_export_csv(args, db: DatabaseManager):
    out_path = args.output_path or "data/clinical_trials_export.csv"
    trials = db.list_trials(limit=1000)
    if not trials:
        console.print("[yellow]No trials in database to export. Run `python cli.py scan` first.[/yellow]")
        return
    ReportExporter.export_trials_to_csv(trials, out_path)
    console.print(f"[green]+ Exported {len(trials)} trials to [bold]{out_path}[/bold][/green]")


def handle_serve():
    import subprocess
    console.print("[bold cyan][LAUNCH] Launching BioCatalyst Streamlit Interactive Dashboard...[/bold cyan]")
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description="BioCatalyst - Autonomous Clinical Trial & Financial Intelligence Engine")
    subparsers = parser.add_subparsers(dest="command")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan ClinicalTrials.gov for active Phase 2/3 trials")
    scan_parser.add_argument("--query", "-q", help="Free text query (e.g. mRNA, KRAS)")
    scan_parser.add_argument("--condition", "-c", help="Disease condition (e.g. Melanoma, Obesity)")
    scan_parser.add_argument("--sponsor", "-s", help="Sponsor organization (e.g. Moderna, Viking)")
    scan_parser.add_argument("--limit", "-l", type=int, default=15, help="Max results to fetch")

    # Financials command
    fin_parser = subparsers.add_parser("financials", help="Audit company cash runway and dilution risk")
    fin_parser.add_argument("ticker", nargs="?", help="Stock ticker (e.g. MRNA, VKTX)")

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Run 3-agent AI diligence committee on an NCT study")
    audit_parser.add_argument("nct_id", help="NCT trial identifier (e.g. NCT03897881)")
    audit_parser.add_argument("--export-md", action="store_true", help="Export markdown audit dossier")

    # Watchlist command
    wl_parser = subparsers.add_parser("watchlist", help="Manage catalyst watchlist")
    wl_parser.add_argument("action", nargs="?", choices=["list", "add", "remove"], default="list")
    wl_parser.add_argument("identifier", nargs="?", help="Ticker or NCT ID")
    wl_parser.add_argument("--alias", help="Optional label or name")
    wl_parser.add_argument("--notes", help="Optional thesis notes")

    # Export CSV
    exp_parser = subparsers.add_parser("export-csv", help="Export trials database to CSV")
    exp_parser.add_argument("output_path", nargs="?", default="data/trials_export.csv")

    # Serve command
    subparsers.add_parser("serve", help="Launch the Streamlit interactive dashboard")

    args = parser.parse_args()

    db = DatabaseManager()
    ct_client = ClinicalTrialsClient()
    mkt_client = MarketDataClient()

    if args.command == "scan":
        handle_scan(args, db, ct_client)
    elif args.command == "financials":
        handle_financials(args, db, mkt_client)
    elif args.command == "audit":
        handle_audit(args, db, ct_client, mkt_client)
    elif args.command == "watchlist":
        handle_watchlist(args, db)
    elif args.command == "export-csv":
        handle_export_csv(args, db)
    elif args.command == "serve":
        handle_serve()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
