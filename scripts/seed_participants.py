import asyncio
import os
from datetime import UTC, datetime

import motor.motor_asyncio
from dotenv import load_dotenv


load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "persuasive_ai_study")


async def main() -> None:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    participants = db["participants"]

    await participants.create_index("participant_id", unique=True)

    seed_rows = [
        {
            "participant_id": "participant-123",
            "status": "active",
            "source": "local-seed",
            "created_at": datetime.now(UTC),
        },
        {
            "participant_id": "participant-456",
            "status": "active",
            "source": "local-seed",
            "created_at": datetime.now(UTC),
        },
        {
            "participant_id": "participant-disabled",
            "status": "disabled",
            "source": "local-seed",
            "created_at": datetime.now(UTC),
        },
    ]

    for row in seed_rows:
        await participants.update_one(
            {"participant_id": row["participant_id"]},
            {"$set": row},
            upsert=True,
        )

    print(f"Seeded {len(seed_rows)} participants into {DATABASE_NAME}.participants")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
