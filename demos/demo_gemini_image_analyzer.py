"""
Gemini Content Analyzer Demo
Demonstrates image analysis capabilities using Google's Gemini model via API key.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.image.analyzers.gemini_content_analyzer import GeminiContentAnalyzer

console = Console()

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


def display_analysis_results(results: dict[str, Any]) -> None:
    """Display analysis results in a formatted way."""

    # Risk Score Panel
    risk_score = results.get("risk_score", 0.0)
    risk_color = "green" if risk_score < 0.3 else "yellow" if risk_score < 0.7 else "red"
    console.print(
        Panel(
            f"[bold {risk_color}]Risk Score: {risk_score:.2f}[/bold {risk_color}]",
            title="Overall Risk Assessment",
            border_style=risk_color,
        )
    )

    # Summary
    if results.get("summary"):
        console.print(Panel(results["summary"], title="[bold]Summary[/bold]", border_style="blue"))

    # Indicators Table
    indicators = results.get("indicators", [])
    if indicators:
        table = Table(title="Detected Indicators", show_header=True, header_style="bold cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Indicator", style="cyan")
        table.add_column("Severity", style="white")
        table.add_column("Details", style="white", width=50)

        for indicator in indicators:
            severity_color = {
                "HIGH": "red",
                "MEDIUM": "yellow",
                "LOW": "green",
                "INFO": "blue",
            }.get(indicator.get("severity", "INFO"), "white")

            table.add_row(
                indicator.get("type", "Unknown"),
                indicator.get("indicator", "Unknown"),
                f"[{severity_color}]{indicator.get('severity', 'Unknown')}[/{severity_color}]",
                indicator.get("details", "No details"),
            )

        console.print(table)

    # Individual Image Analyses
    analyses = results.get("analysis_details", {}).get("individual_analyses", [])
    if analyses:
        console.print("\n[bold cyan]Individual Image Analyses:[/bold cyan]\n")

        for analysis in analyses:
            content = []

            if analysis.get("primary_label"):
                content.append(f"[yellow]Primary Label:[/yellow] {analysis['primary_label']}")

            if analysis.get("labels"):
                content.append(f"[yellow]Labels:[/yellow] {', '.join(analysis['labels'][:5])}")

            if analysis.get("description"):
                content.append(f"[yellow]Description:[/yellow] {analysis['description'][:200]}...")

            if analysis.get("safety_score") is not None:
                safety_color = (
                    "green"
                    if analysis["safety_score"] > 0.7
                    else "yellow" if analysis["safety_score"] > 0.3 else "red"
                )
                content.append(
                    f"[yellow]Safety Score:[/yellow] [{safety_color}]{analysis['safety_score']:.2f}[/{safety_color}]"
                )

            if analysis.get("on_running_related"):
                confidence = analysis.get("on_running_confidence", 0.0)
                content.append(
                    f"[green]On Running Related[/green] (confidence: {confidence:.2f})"
                )
                if analysis.get("on_running_details"):
                    content.append(f"  Details: {analysis['on_running_details']}")

            if analysis.get("detected_brands"):
                content.append(
                    f"[yellow]Brands Detected:[/yellow] {', '.join(analysis['detected_brands'])}"
                )

            if analysis.get("text_detected"):
                content.append(
                    f"[yellow]Text Detected:[/yellow] {analysis['text_detected'][:200]}"
                )

            panel_title = f"Image {analysis.get('image_index', 0) + 1}"
            panel_color = "red" if analysis.get("contains_harmful_content") else "green"

            console.print(
                Panel(
                    "\n".join(content),
                    title=f"[bold]{panel_title}[/bold]",
                    border_style=panel_color,
                )
            )


def analyze_test_images(analyzer: GeminiContentAnalyzer) -> None:
    """Analyze a set of test images."""

    test_images = [
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff",
        "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b",
    ]

    console.print(f"\n[cyan]Analyzing {len(test_images)} test images...[/cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Analyzing {len(test_images)} images...", total=len(test_images))
        results = analyzer.analyze_images(test_images)
        progress.update(task, completed=len(test_images))

    display_analysis_results(results)


def analyze_on_running_images(analyzer: GeminiContentAnalyzer) -> None:
    """Analyze images that should be related to On Running."""

    console.print("\n[bold cyan]On Running Brand Detection Test[/bold cyan]\n")

    on_running_test = [
        "https://images.unsplash.com/photo-1539185441755-769473a23570",
        "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a",
    ]

    console.print("[yellow]Testing brand detection on athletic footwear images...[/yellow]")

    results = analyzer.analyze_images(on_running_test)

    on_running_found = False
    for analysis in results.get("analysis_details", {}).get("individual_analyses", []):
        if analysis.get("on_running_related"):
            on_running_found = True
            console.print(
                Panel(
                    f"[green]On Running content detected![/green]\n"
                    f"Confidence: {analysis.get('on_running_confidence', 0.0):.2%}\n"
                    f"Details: {analysis.get('on_running_details', 'No details')}",
                    border_style="green",
                    title="Brand Detection Success",
                )
            )

    if not on_running_found:
        console.print("[yellow]No On Running content detected in test images[/yellow]")

    display_analysis_results(results)


def analyze_harmful_content_detection(analyzer: GeminiContentAnalyzer) -> None:
    """Test harmful content detection (using safe test images)."""

    console.print("\n[bold cyan]Safety Detection Test[/bold cyan]\n")
    console.print("[yellow]Testing with safe images to verify safety scoring...[/yellow]")

    safe_test = [
        "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba",
        "https://images.unsplash.com/photo-1552053831-71594a27632d",
    ]

    results = analyzer.analyze_images(safe_test)

    all_safe = True
    for analysis in results.get("analysis_details", {}).get("individual_analyses", []):
        safety_score = analysis.get("safety_score", 1.0)
        if safety_score < 0.7:
            all_safe = False

        if analysis.get("contains_harmful_content"):
            console.print(
                f"[red]Harmful content detected in image {analysis.get('image_index', 0) + 1}[/red]"
            )

    if all_safe:
        console.print("[green]All test images passed safety checks[/green]")

    display_analysis_results(results)


def main() -> int:
    """Run the Gemini Content Analyzer demo."""

    console.print(
        Panel(
            "[bold]Gemini Content Analyzer Demo[/bold]\n"
            + "AI-powered image analysis\n"
            + "Features: Content labeling, safety detection, brand recognition, OCR",
            border_style="blue",
            title="[bold white]Image Analysis Platform[/bold white]",
        )
    )

    # Check for API key
    if not GEMINI_API_KEY:
        console.print(
            Panel(
                "[red]Error: GEMINI_API_KEY environment variable is not set[/red]\n"
                + "Set it in your .env file or export it:\n"
                + "  export GEMINI_API_KEY=your-key-here",
                border_style="red",
            )
        )
        return 1

    # Initialize analyzer
    console.print("\n[yellow]Initializing Gemini Content Analyzer...[/yellow]")

    try:
        analyzer = GeminiContentAnalyzer(
            api_key=GEMINI_API_KEY,
            model_name=GEMINI_MODEL,
            temperature=0.3,
        )
        console.print("[green]Analyzer initialized successfully[/green]")
    except Exception as e:
        console.print(f"[red]Failed to initialize analyzer: {e}[/red]")
        return 1

    # Run demo scenarios
    try:
        console.print(Panel("[bold]Test 1: General Image Analysis[/bold]", border_style="cyan"))
        analyze_test_images(analyzer)

        console.print(Panel("[bold]Test 2: Brand Detection[/bold]", border_style="cyan"))
        analyze_on_running_images(analyzer)

        console.print(Panel("[bold]Test 3: Safety Analysis[/bold]", border_style="cyan"))
        analyze_harmful_content_detection(analyzer)

        console.print(
            Panel(
                "[green]All tests completed successfully![/green]\n\n"
                + "The Gemini Content Analyzer provides:\n"
                + "  - Comprehensive image labeling and description\n"
                + "  - Harmful content detection with safety scoring\n"
                + "  - On Running brand and product detection\n"
                + "  - Text extraction from images (OCR)\n"
                + "  - Scene and quality analysis",
                border_style="green",
                title="[bold]Demo Complete[/bold]",
            )
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"\n[red]Demo failed with error: {e}[/red]")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
