import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import close_mongo_connection, connect_to_mongo
from app.services.demo_reset_service import preview_demo_reset, reset_demo_data


async def run(admin_email: str, confirm: bool) -> None:
    await connect_to_mongo()
    try:
        result = await (reset_demo_data(admin_email) if confirm else preview_demo_reset(admin_email))
        print(f"Retained admin: {result['retained_admin']}")
        if confirm:
            for collection, count in result["deleted"].items():
                print(f"Deleted {collection}: {count}")
            print("Database reset completed.")
        else:
            for collection, count in result["records_to_remove"].items():
                print(f"Would delete {collection}: {count}")
            print("Dry run only. Re-run with --confirm to delete these records.")
    finally:
        await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove FleetOpt demo data while retaining one administrator account.")
    parser.add_argument("--admin-email", default="admin@fleet.local")
    parser.add_argument("--confirm", action="store_true", help="Perform deletion. Without this flag the script is read-only.")
    args = parser.parse_args()
    asyncio.run(run(args.admin_email, args.confirm))


if __name__ == "__main__":
    main()
