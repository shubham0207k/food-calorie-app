"""Command-line entry point for USDA FoodData Central matching."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


USDA_DIR = Path(__file__).resolve().parent
MIGRATION_DIR = USDA_DIR.parent / "migration"

if str(MIGRATION_DIR) not in sys.path:
    sys.path.append(str(MIGRATION_DIR))

from migration_utils import (
    CATEGORY_ALIASES,
    SUPPORTED_CATEGORY_SET,
    canonical_json,
    collection_payload,
    load_collection,
    load_manifest,
    write_if_changed,
)

try:
    from .config import CONFIDENCE_THRESHOLD
    from .matcher import has_existing_usda, match_food
    from .report import MatchStats, print_matching_report
except ImportError:
    from config import CONFIDENCE_THRESHOLD
    from matcher import has_existing_usda, match_food
    from report import MatchStats, print_matching_report


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for USDA matching."""

    project_root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description="Match FoodVision knowledge-base foods to USDA records."
    )
    parser.add_argument(
        "--knowledge-base-dir",
        type=Path,
        default=project_root / "data" / "knowledge_base",
        help="Path to the FoodVision knowledge_base directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report matches without writing collection files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing USDA values.",
    )
    parser.add_argument(
        "--category",
        help="Only match foods in one category, such as fruits.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of eligible foods to process.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="Minimum accepted confidence score.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")

    if not 0 <= args.min_confidence <= 1:
        parser.error("--min-confidence must be between 0.00 and 1.00")

    if args.category:
        try:
            args.category = normalize_category(args.category)
        except ValueError as exc:
            parser.error(str(exc))

    return args


def normalize_category(category: str) -> str:
    """Normalize a CLI category value to a supported category name."""

    key = " ".join(category.strip().lower().replace("_", " ").split())
    normalized = CATEGORY_ALIASES.get(key, category.strip())

    if normalized not in SUPPORTED_CATEGORY_SET:
        valid = ", ".join(sorted(SUPPORTED_CATEGORY_SET))
        raise ValueError(f"Unknown category '{category}'. Valid categories: {valid}")

    return normalized


def _food_label(food: Any, fallback: str) -> str:
    if not isinstance(food, dict):
        return fallback

    display_name = food.get("display_name")

    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()

    food_id = food.get("id")

    if isinstance(food_id, str) and food_id.strip():
        return food_id.strip()

    return fallback


def _matches_category(food: Any, category: str | None) -> bool:
    if category is None:
        return True

    return isinstance(food, dict) and food.get("category") == category


def match_knowledge_base(
    knowledge_base_dir: Path,
    dry_run: bool = False,
    overwrite: bool = False,
    category: str | None = None,
    limit: int | None = None,
    min_confidence: float = CONFIDENCE_THRESHOLD,
) -> MatchStats:
    """Match eligible knowledge-base foods to USDA records."""

    stats = MatchStats()
    manifest = load_manifest(knowledge_base_dir)
    collection_files = [
        load_collection(knowledge_base_dir, filename)
        for filename in manifest["collections"]
    ]
    limit_reached = False

    for collection in collection_files:
        updated_foods = list(collection.foods)
        collection_changed = False

        for index, food in enumerate(collection.foods):
            if not _matches_category(food, category):
                continue

            if limit is not None and stats.foods_processed >= limit:
                limit_reached = True
                break

            fallback = f"{collection.filename}[{index}]"
            food_name = _food_label(food, fallback)
            stats.foods_processed += 1

            if not isinstance(food, dict):
                stats.skipped += 1
                stats.unmatched_foods.append(food_name)
                stats.add_warning(f"Skipped non-object food in {fallback}")
                continue

            if has_existing_usda(food.get("usda")) and not overwrite:
                stats.already_matched += 1
                continue

            result = match_food(
                food=food,
                min_confidence=min_confidence,
            )
            stats.add_warning(result.warning)

            if result.status == "matched" and result.usda is not None:
                stats.matched += 1
                stats.confidences.append(result.confidence)

                updated_food = dict(food)
                updated_food["usda"] = result.usda
                updated_foods[index] = updated_food
                collection_changed = True
            elif result.status == "skipped":
                stats.skipped += 1
            else:
                stats.unmatched_foods.append(food_name)

        if collection_changed:
            final_payload = collection_payload(collection, updated_foods)

            if canonical_json(final_payload) != canonical_json(collection.payload):
                stats.collections_updated += 1

                if not dry_run:
                    write_if_changed(
                        collection.path,
                        final_payload,
                        collection.payload,
                    )

        if limit_reached:
            break

    print_matching_report(stats, dry_run=dry_run)
    return stats


if __name__ == "__main__":
    args = parse_args()
    match_knowledge_base(
        knowledge_base_dir=args.knowledge_base_dir,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        category=args.category,
        limit=args.limit,
        min_confidence=args.min_confidence,
    )
