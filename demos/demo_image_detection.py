#!/usr/bin/env python3
"""
Beautiful AI Image Detection Demo
Showcases the GenAIDetectionAnalyzer with rich visual output
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from PIL import Image
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.image.analyzers.genai_detection_analyzer import GenAIDetectionAnalyzer

logger.remove()
logger.add(sys.stderr, level="ERROR")

console = Console()


def create_header() -> Panel:
    """Create a beautiful header for the demo."""
    header_text = """
    🤖 AI vs Human Image Detection Demo 👤
    """
    return Panel(
        Align.center(Text(header_text.strip(), style="bold cyan")),
        border_style="blue",
        padding=(1, 2),
    )


def initialize_analyzer() -> GenAIDetectionAnalyzer:
    """Initialize the analyzer with progress display."""
    console.print(create_header())

    project_root = Path(__file__).parent.parent
    model_path = project_root / "models"

    if model_path.exists():
        analyzer = GenAIDetectionAnalyzer(local_model_path=str(model_path))
    else:
        analyzer = GenAIDetectionAnalyzer()

    if analyzer.ai_detector_model and analyzer.ai_detector_processor:
        console.print(Panel("[green]✓ Model loaded successfully![/green]", border_style="green"))
    else:
        console.print(Panel("[red]✗ Failed to load model[/red]", border_style="red"))
        sys.exit(1)

    return analyzer


def get_test_images() -> dict[str, Path]:
    """Get all images from the test directory."""
    # Start from script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check multiple possible locations
    possible_dirs = [
        project_root / "images",  # Project root images
    ]

    images = {}
    for test_dir in possible_dirs:
        if test_dir.exists():
            # console.print(f"[dim]Found image directory: {test_dir}[/dim]")
            for img_path in test_dir.glob("*"):
                if img_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]:
                    images[img_path.stem] = img_path
            if images:
                break  # Stop at first directory with images

    return images


def analyze_image(analyzer: GenAIDetectionAnalyzer, image_path: Path) -> dict[str, Any]:
    """Analyze a single image and return results."""
    # Pass the path directly as a string
    result = analyzer.check_ai_generated(str(image_path.absolute()))

    # Get image dimensions
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            format_type = img.format
    except Exception as e:
        logger.error(f"Could not open image {e}")
        width, height, format_type = 0, 0, "Unknown"

    return {
        "filename": image_path.name,
        "path": str(image_path),
        "width": width,
        "height": height,
        "format": format_type,
        "is_ai": result.get("is_ai", False),
        "confidence": result.get("confidence", 0),
        "predicted_label": result.get("predicted_label", "Unknown"),
        "ai_probability": result.get("ai_probability", 0),
        "human_probability": result.get("human_probability", 0),
        "class_probabilities": result.get("class_probabilities", {}),
        "error": result.get("error", None),
    }


def create_results_table(results: list[dict[str, Any]]) -> Table:
    """Create a beautiful results table."""
    table = Table(
        title="🎯 Classification Results",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        title_style="bold white",
        expand=True,
        show_lines=True,
    )
    # Add columns
    table.add_column("📁 File", style="yellow", no_wrap=True, width=30)
    table.add_column("📐 Dimensions", justify="center", style="dim")
    table.add_column("🎯 Prediction", justify="center", width=20)
    table.add_column("💯 Confidence", justify="center", width=15)
    table.add_column("🤖 AI Score", justify="right", style="red", width=12)
    table.add_column("👤 Human Score", justify="right", style="green", width=12)
    table.add_column("📊 Visual", justify="left", width=25)  # Changed to left justify

    # Add rows
    for r in results:
        # Prediction with icon
        if r["is_ai"]:
            pred_text = "[bold red]🤖 AI-GENERATED[/bold red]"
        else:
            pred_text = "[bold green]👤 HUMAN-CREATED[/bold green]"

        # Confidence with color
        conf_pct = r["confidence"] * 100
        if conf_pct >= 90:
            conf_style = "bold green"
        elif conf_pct >= 70:
            conf_style = "yellow"
        else:
            conf_style = "red"
        conf_text = f"[{conf_style}]{conf_pct:.1f}%[/{conf_style}]"

        # Visual probability bar with fixed center
        ai_bar_count = int(r["ai_probability"] * 10)
        human_bar_count = int(r["human_probability"] * 10)

        # Build the visual bar with exact positioning
        # Total width = 25 (column width)
        # Center position = 12 (for the pipe)
        # AI bars: positions 2-11 (10 chars, right-aligned)
        # Pipe: position 12
        # Human bars: positions 13-22 (10 chars, left-aligned)

        # Create 10-char AI side (right-aligned)
        ai_side = ("█" * ai_bar_count).rjust(10)

        # Create 10-char Human side (left-aligned)
        human_side = ("█" * human_bar_count).ljust(10)

        # Add padding to center the whole bar in the 25-char column
        # 2 spaces before, then 21-char bar (10 + 1 + 10), then 2 spaces after
        visual_bar = f"  [red]{ai_side}[/red]|[green]{human_side}[/green]  "

        # Alternative approach: if the above doesn't work, try this instead:
        # visual_bar = f"[red]{ai_side}[/red]|[green]{human_side}[/green]".center(25)
        # But Rich color codes might interfere with .center()

        # Dimensions
        dims = f"{r['width']}×{r['height']}" if r["width"] > 0 else "N/A"

        table.add_row(
            r["filename"],
            dims,
            pred_text,
            conf_text,
            f"{r['ai_probability']:.3f}",
            f"{r['human_probability']:.3f}",
            visual_bar,
        )

    return table


def run_demo() -> int:
    """Run the beautiful demo."""
    try:
        # Initialize analyzer
        analyzer = initialize_analyzer()

        # Get test images
        # console.print("\n[cyan]Scanning for test images...[/cyan]")
        images = get_test_images()

        if not images:
            # Define paths for error message
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

            console.print(
                Panel(
                    "[red]No test images found![/red]\n\n"
                    + "Please add images to one of these directories:\n"
                    + f"  • {project_root}/tests/images/\n"
                    + f"  • {project_root}/images/\n"
                    + f"  • {script_dir}/images/",
                    border_style="red",
                )
            )
            return 1

        # console.print(f"[green]Found {len(images)} images to analyze[/green]\n")

        # Analyze images with progress
        results = []
        for _, path in sorted(images.items()):
            result = analyze_image(analyzer, path)
            results.append(result)

        # Display results
        # console.print("\n")
        console.print(create_results_table(results))

        # Final message
        console.print(
            Panel(
                "[green]✨ Demo completed successfully![/green]",
                border_style="green",
                title="[bold]Complete[/bold]",
            )
        )

        return 0

    except Exception as e:
        console.print(
            Panel(
                f"[red]Demo failed with error:[/red]\n{str(e)}",
                border_style="red",
                title="[bold]Error[/bold]",
            )
        )
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())
