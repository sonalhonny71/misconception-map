#!/usr/bin/env python3
"""
Content seeding script - loads YAML content into the database.
Run after migrations (from the backend/ folder):  python scripts/seed_content.py
(The app also does this automatically when it starts.)
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.content.seed import seed_content  # noqa: E402


def main():
    db = SessionLocal()
    try:
        created, updated = seed_content(db)
        print(f"Content seeding complete: {created} new, {updated} updated")
    except Exception as e:
        db.rollback()
        print(f"Error seeding content: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
