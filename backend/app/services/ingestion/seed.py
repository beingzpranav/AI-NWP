"""
Database seeder — inserts default locations on first startup.
Run once via: python -m app.services.ingestion.seed
"""
import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal, init_db
from app.models.location import Location
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_LOCATIONS = [
    {"name": "New Delhi",  "city": "New Delhi",  "country": "India", "latitude": 28.6139, "longitude": 77.2090, "timezone": "Asia/Kolkata"},
    {"name": "Jaipur",     "city": "Jaipur",     "country": "India", "latitude": 26.9124, "longitude": 75.7873, "timezone": "Asia/Kolkata"},
    {"name": "Bengaluru",  "city": "Bengaluru",  "country": "India", "latitude": 12.9716, "longitude": 77.5946, "timezone": "Asia/Kolkata"},
    {"name": "Hyderabad",  "city": "Hyderabad",  "country": "India", "latitude": 17.3850, "longitude": 78.4867, "timezone": "Asia/Kolkata"},
    {"name": "Mumbai",     "city": "Mumbai",     "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
    {"name": "Chennai",    "city": "Chennai",    "country": "India", "latitude": 13.0827, "longitude": 80.2707, "timezone": "Asia/Kolkata"},
    {"name": "Kolkata",    "city": "Kolkata",    "country": "India", "latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"},
    {"name": "Pune",       "city": "Pune",       "country": "India", "latitude": 18.5204, "longitude": 73.8567, "timezone": "Asia/Kolkata"},
    {"name": "Ahmedabad",  "city": "Ahmedabad",  "country": "India", "latitude": 23.0225, "longitude": 72.5714, "timezone": "Asia/Kolkata"},
    {"name": "Lucknow",    "city": "Lucknow",    "country": "India", "latitude": 26.8467, "longitude": 80.9462, "timezone": "Asia/Kolkata"},
    {"name": "Chandigarh", "city": "Chandigarh", "country": "India", "latitude": 30.7333, "longitude": 76.7794, "timezone": "Asia/Kolkata"},
    {"name": "Bhopal",     "city": "Bhopal",     "country": "India", "latitude": 23.2599, "longitude": 77.4126, "timezone": "Asia/Kolkata"},
    {"name": "Patna",      "city": "Patna",      "country": "India", "latitude": 25.5941, "longitude": 85.1376, "timezone": "Asia/Kolkata"},
    {"name": "Kochi",      "city": "Kochi",      "country": "India", "latitude": 9.9312,  "longitude": 76.2673, "timezone": "Asia/Kolkata"},
]


async def seed_locations() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Location))
        existing = {loc.city.lower() for loc in result.scalars().all() if loc.city}
        
        added = 0
        for loc_data in DEFAULT_LOCATIONS:
            if loc_data["city"].lower() not in existing:
                db.add(Location(**loc_data))
                added += 1
        if added > 0:
            await db.commit()
            logger.info("seed_done", locations_added=added)
        else:
            logger.info("seed_skip", message="All 14 locations already exist")
        return added


async def main():
    await init_db()
    added = await seed_locations()
    print(f"Seeded {added} locations.")


if __name__ == "__main__":
    asyncio.run(main())
