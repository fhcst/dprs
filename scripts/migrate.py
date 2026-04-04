"""
Migration CLI for the daily-training-submit-system.

Usage:
    uv run python scripts/migrate.py init
    uv run python scripts/migrate.py up
    uv run python scripts/migrate.py down
    uv run python scripts/migrate.py status
"""
import asyncio
import importlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel, Field

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
COLLECTION_NAME = "migrations"
MIGRATION_PATTERN = re.compile(r"^\d{8}_\d{3}_\w+\.py$")

# Add project root to sys.path so `scripts.migrations.*` can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add src directory to sys.path so migration files can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MigrationRecord(BaseModel):
    filename: str
    direction: str
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


async def get_applied_migrations(db: AsyncIOMotorDatabase) -> list[str]:
    """Return list of filenames that have been applied (forward - backward)."""
    collection = db[COLLECTION_NAME]
    cursor = collection.find({"direction": "forward"}, {"filename": 1})
    forward = {doc["filename"] async for doc in cursor}

    cursor = collection.find({"direction": "backward"}, {"filename": 1})
    backward = {doc["filename"] async for doc in cursor}

    # Applied = forwarded but not rolled back
    # Count occurrences: if forward > backward, it's applied
    all_forward = await db[COLLECTION_NAME].count_documents({"direction": "forward"})
    applied = []
    for filename in sorted(forward):
        fwd_count = await db[COLLECTION_NAME].count_documents(
            {"filename": filename, "direction": "forward"}
        )
        bwd_count = await db[COLLECTION_NAME].count_documents(
            {"filename": filename, "direction": "backward"}
        )
        if fwd_count > bwd_count:
            applied.append(filename)

    return applied


async def record_migration(
    db: AsyncIOMotorDatabase, filename: str, direction: str
) -> None:
    """Record a migration execution, preventing duplicate forward records."""
    if direction == "forward":
        existing = await db[COLLECTION_NAME].find_one(
            {"filename": filename, "direction": "forward"}
        )
        if existing:
            return  # idempotency: skip duplicate forward records

    record = MigrationRecord(filename=filename, direction=direction)
    await db[COLLECTION_NAME].insert_one(record.model_dump())


def _get_migration_files() -> list[str]:
    """Return sorted list of migration filenames."""
    if not MIGRATIONS_DIR.exists():
        return []
    files = [
        f.name
        for f in MIGRATIONS_DIR.iterdir()
        if MIGRATION_PATTERN.match(f.name) and f.name != "__init__.py"
    ]
    return sorted(files)


def _load_migration(filename: str) -> Any:
    """Import a migration module by filename."""
    module_path = f"scripts.migrations.{filename[:-3]}"  # strip .py
    return importlib.import_module(module_path)


async def cmd_init(db: AsyncIOMotorDatabase) -> None:
    """Create migration tracking collection and index."""
    await db[COLLECTION_NAME].create_index("filename")
    await db[COLLECTION_NAME].create_index([("filename", 1), ("direction", 1)])
    print("✓ Migration tracking collection initialized.")


async def cmd_up(db: AsyncIOMotorDatabase) -> None:
    """Apply all pending migrations."""
    applied = await get_applied_migrations(db)
    pending = [f for f in _get_migration_files() if f not in applied]

    if not pending:
        print("Nothing to migrate.")
        return

    for filename in pending:
        print(f"→ Applying {filename}...")
        mod = _load_migration(filename)
        await mod.forward()
        await record_migration(db, filename, "forward")
        print(f"  ✓ {filename}")


async def cmd_down(db: AsyncIOMotorDatabase) -> None:
    """Roll back the most recently applied migration."""
    applied = await get_applied_migrations(db)
    if not applied:
        print("No migrations to roll back.")
        return

    last = applied[-1]
    print(f"← Rolling back {last}...")
    mod = _load_migration(last)
    await mod.backward()
    await record_migration(db, last, "backward")
    print(f"  ✓ Rolled back {last}")


async def cmd_status(db: AsyncIOMotorDatabase) -> None:
    """Show applied and pending migrations."""
    applied = await get_applied_migrations(db)
    all_files = _get_migration_files()

    print(f"{'Status':<10} {'Migration'}")
    print("-" * 60)
    for f in all_files:
        status = "applied" if f in applied else "pending"
        print(f"{status:<10} {f}")

    if not all_files:
        print("No migration files found.")


async def _main(command: str) -> None:
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "dts2")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    try:
        if command == "init":
            await cmd_init(db)
        elif command == "up":
            await cmd_up(db)
        elif command == "down":
            await cmd_down(db)
        elif command == "status":
            await cmd_status(db)
        else:
            print(f"Unknown command: {command}")
            print("Usage: migrate.py [init|up|down|status]")
            sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: migrate.py [init|up|down|status]")
        sys.exit(1)

    asyncio.run(_main(sys.argv[1]))
