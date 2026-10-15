"""
Content Loader - Loads items from YAML files and provides query methods.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache


class ContentLoader:
    """Loads and indexes content items from YAML files."""

    def __init__(self, content_dir: Path):
        self.content_dir = content_dir
        self._items_cache: Dict[str, Dict] = {}
        self._items_by_level: Dict[int, List[Dict]] = {}
        self._items_by_kind: Dict[str, List[Dict]] = {}
        self._load_all()

    def _load_all(self):
        """Load all YAML files from content directory."""
        for yaml_file in self.content_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "items" in data:
                    for item in data["items"]:
                        self._index_item(item)

    def _index_item(self, item: Dict):
        """Index an item by ID, level, and kind."""
        item_id = item["item_id"]
        self._items_cache[item_id] = item

        level = item["level"]
        if level not in self._items_by_level:
            self._items_by_level[level] = []
        self._items_by_level[level].append(item)

        kind = item["kind"]
        if kind not in self._items_by_kind:
            self._items_by_kind[kind] = []
        self._items_by_kind[kind].append(item)

    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        return self._items_cache.get(item_id)

    def get_diagnostic_items(self, level: int) -> List[Dict]:
        return [
            item for item in self._items_by_level.get(level, [])
            if item["kind"] == "diagnostic"
        ]

    def get_followup_items(self, level: int, misconception_id: Optional[str]) -> List[Dict]:
        if not misconception_id:
            return []
        return [
            item for item in self._items_by_level.get(level, [])
            if item["kind"] == "followup" and misconception_id in item.get("discriminates", [])
        ]

    def get_check_items(self, level: int) -> List[Dict]:
        return [
            item for item in self._items_by_level.get(level, [])
            if item["kind"] == "check"
        ]

    def get_practice_items(self, level: int, misconception_id: Optional[str], seen_responses: List[Dict]) -> List[Dict]:
        seen_item_ids = {r["item_id"] for r in seen_responses}
        candidates = [
            item for item in self._items_by_level.get(level, [])
            if item["kind"] == "practice"
            and item["item_id"] not in seen_item_ids
            and (not misconception_id or misconception_id in item.get("targets", []))
        ]
        # A practice set is 3 questions: if there are fewer targeted items than that
        # (or none), top up with general practice items for the level.
        if len(candidates) < 3:
            extra = [
                item for item in self._items_by_level.get(level, [])
                if item["kind"] == "practice"
                and item["item_id"] not in seen_item_ids
                and item not in candidates
            ]
            candidates = candidates + extra
        return candidates[:6]  # Return up to 6, engine will use first 3

    def get_retest_items(self, level: int, skill: str, seen_item_ids: set) -> List[Dict]:
        candidates = [
            item for item in self._items_by_level.get(level, [])
            if item["kind"] == "retest"
            and item["item_id"] not in seen_item_ids
        ]
        return candidates[:6]  # Return up to 6, engine will use first 3

    def get_primary_skill(self, level: int) -> str:
        skills = {
            1: "arithmetic-integers",
            2: "expressions-like-terms",
            3: "distributive-inverse",
            4: "multi-step-equations",
            5: "transfer-inequalities",
        }
        return skills.get(level, f"level-{level}")

    def get_all_items(self) -> List[Dict]:
        return list(self._items_cache.values())


@lru_cache(maxsize=1)
def get_content_loader() -> ContentLoader:
    content_dir = Path(__file__).parent.parent / "content"
    return ContentLoader(content_dir)