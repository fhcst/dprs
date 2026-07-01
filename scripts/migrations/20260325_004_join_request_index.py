"""
Create partial unique index for join_requests collection.

Ensures only one pending JoinRequest per (class_id, user_id) pair.
"""
import os

from motor.motor_asyncio import AsyncIOMotorClient


async def _get_db():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "dts2")
    client = AsyncIOMotorClient(mongo_url)
    return client, client[db_name]


async def forward() -> None:
    """Create partial unique index on join_requests (class_id, user_id) where status=pending."""
    client, db = await _get_db()
    try:
        await db["join_requests"].create_index(
            [("class_id", 1), ("user_id", 1)],
            unique=True,
            partialFilterExpression={"status": "pending"},
            name="unique_pending_per_class_user",
        )
    finally:
        client.close()


async def backward() -> None:
    """Drop the partial unique index."""
    client, db = await _get_db()
    try:
        await db["join_requests"].drop_index("unique_pending_per_class_user")
    except Exception:
        pass
    finally:
        client.close()
