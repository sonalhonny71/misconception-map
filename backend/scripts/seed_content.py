#!/usr/bin/env python3
"""
Content seeding script - loads YAML content into database.
Run after migrations: python backend/scripts/seed_content.py
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, SessionLocal
from app.db.models import Item
from app.content.loader import ContentLoader


def seed_content():
    """Load all YAML content into database."""
    content_loader = ContentLoader(Path(__file__).parent.parent / "app" / "content")
    all_items = content_loader.get_all_items()
    
    db = SessionLocal()
    try:
        seeded = 0
        updated = 0
        
        for item_data in all_items:
            # Check if item exists
            existing = db.query(Item).filter(Item.item_id == item_data["item_id"]).first()
            
            if existing:
                # Update existing
                existing.level = item_data["level"]
                existing.skill = item_data["skill"]
                existing.kind = item_data["kind"]
                existing.prompt = item_data["prompt"]
                existing.options = json.dumps(item_data["options"]) if isinstance(item_data["options"], list) else item_data["options"]
                existing.correct_option_id = item_data["correct_option_id"]
                existing.explanation = item_data["explanation"]
                existing.discriminates = json.dumps(item_data["discriminates"]) if item_data.get("discriminates") else None
                updated += 1
            else:
                # Create new
                item = Item(
                    item_id=item_data["item_id"],
                    level=item_data["level"],
                    skill=item_data["skill"],
                    kind=item_data["kind"],
                    prompt=item_data["prompt"],
                    options=json.dumps(item_data["options"]) if isinstance(item_data["options"], list) else item_data["options"],
                    correct_option_id=item_data["correct_option_id"],
                    explanation=item_data["explanation"],
                    discriminates=json.dumps(item_data["discriminates"]) if item_data.get("discriminates") else None,
                )
                db.add(item)
                seeded += 1
        
        db.commit()
        print(f"Content seeding complete: {seeded} new, {updated} updated")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding content: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_content()