"""
Content seeding - copies the YAML content into the `items` table.

Safe to run many times: existing items are updated, new ones are added.
Used both by the app at start-up and by scripts/seed_content.py.
"""

import json
from pathlib import Path
from typing import Tuple

from sqlalchemy.orm import Session

from app.content.loader import ContentLoader
from app.db.models import Item

CONTENT_DIR = Path(__file__).resolve().parent


def _as_json(value):
    return json.dumps(value) if isinstance(value, list) else value


def seed_content(db: Session) -> Tuple[int, int]:
    """Load all YAML content into the database. Returns (created, updated)."""
    loader = ContentLoader(CONTENT_DIR)
    created = 0
    updated = 0

    for data in loader.get_all_items():
        fields = dict(
            level=data["level"],
            skill=data["skill"],
            kind=data["kind"],
            prompt=data["prompt"],
            options=_as_json(data["options"]),
            correct_option_id=data["correct_option_id"],
            explanation=data["explanation"],
            discriminates=json.dumps(data["discriminates"]) if data.get("discriminates") else None,
        )
        existing = db.query(Item).filter(Item.item_id == data["item_id"]).first()
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(Item(item_id=data["item_id"], **fields))
            created += 1

    db.commit()
    return created, updated
