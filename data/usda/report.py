"""Console reporting for USDA matching."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MatchStats:
    """Counters collected during USDA matching."""

    foods_processed: int = 0
    matched: int = 0
    already_matched: int = 0
    skipped: int = 0
    unmatched: int = 0
    collections_updated: int = 0
    confidences: list[float] = field(default_factory=list)
    unmatched_foods: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, warning: str | None) -> None:
        """Record a warning once."""

        if warning and warning not in self.warnings:
            self.warnings.append(warning)


def _format_confidence(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value:.2f}"


def print_metric(label: str, value: int | str) -> None:
    """Print one aligned report metric."""

    print(f"{label:<28}{value:>8}")


def print_matching_report(stats: MatchStats, dry_run: bool = False) -> None:
    """Print a professional USDA matching summary."""

    average = None
    highest = None
    lowest = None

    if stats.confidences:
        average = sum(stats.confidences) / len(stats.confidences)
        highest = max(stats.confidences)
        lowest = min(stats.confidences)

    print("=" * 41)
    print("USDA Matching Report")
    print("=" * 41)
    print()

    if dry_run:
        print("Mode: DRY RUN")
        print()

    print_metric("Foods Processed:", stats.foods_processed)
    print()
    print_metric("Matched:", stats.matched)
    print()
    print_metric("Already Matched:", stats.already_matched)
    print()
    print_metric("Skipped:", stats.skipped)
    print()
    print_metric("Unmatched:", stats.unmatched)
    print()
    print_metric("Average Confidence:", _format_confidence(average))
    print()
    print_metric("Highest Confidence:", _format_confidence(highest))
    print()
    print_metric("Lowest Accepted:", _format_confidence(lowest))
    print()
    print("=" * 41)

    if stats.unmatched_foods:
        print()
        print("Unmatched Foods")
        print()

        for food_name in stats.unmatched_foods:
            print(f"- {food_name}")

    if stats.warnings:
        print()
        print("Warnings")
        print()

        for warning in stats.warnings:
            print(f"- {warning}")
