"""Location endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.location import Location
from app.schemas.weather import LocationResponse, LocationCreate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=List[LocationResponse])
async def list_locations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location).where(Location.is_active == True))
    return result.scalars().all()


@router.post("/", response_model=LocationResponse, status_code=201)
async def create_location(payload: LocationCreate, db: AsyncSession = Depends(get_db)):
    loc = Location(**payload.model_dump())
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.get("/search/", response_model=List[LocationResponse])
async def search_locations(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Location).where(
            Location.name.ilike(f"%{q}%") | Location.city.ilike(f"%{q}%")
        )
    )
    return result.scalars().all()
