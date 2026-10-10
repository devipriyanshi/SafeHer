from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.contact import EmergencyContact
from backend.schemas.contact import ContactCreate, ContactUpdate


async def _get_or_403(contact_id: int, user_id: int, db: AsyncSession) -> EmergencyContact:
    result = await db.execute(select(EmergencyContact).where(EmergencyContact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    if contact.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return contact


async def list_contacts(user_id: int, db: AsyncSession) -> list[EmergencyContact]:
    result = await db.execute(
        select(EmergencyContact)
        .where(EmergencyContact.user_id == user_id)
        .order_by(EmergencyContact.is_primary.desc(), EmergencyContact.name)
    )
    return list(result.scalars().all())


async def create_contact(user_id: int, payload: ContactCreate, db: AsyncSession) -> EmergencyContact:
    # Only one primary contact allowed
    if payload.is_primary:
        existing = await db.execute(
            select(EmergencyContact).where(
                EmergencyContact.user_id == user_id,
                EmergencyContact.is_primary == True,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A primary contact already exists. Update the existing one first.",
            )

    contact = EmergencyContact(user_id=user_id, **payload.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(contact_id: int, user_id: int, payload: ContactUpdate, db: AsyncSession) -> EmergencyContact:
    contact = await _get_or_403(contact_id, user_id, db)

    if payload.is_primary:
        existing = await db.execute(
            select(EmergencyContact).where(
                EmergencyContact.user_id == user_id,
                EmergencyContact.is_primary == True,
                EmergencyContact.id != contact_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another primary contact already exists.",
            )

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(contact_id: int, user_id: int, db: AsyncSession) -> None:
    contact = await _get_or_403(contact_id, user_id, db)
    await db.delete(contact)
    await db.commit()


async def get_active_contacts(user_id: int, db: AsyncSession) -> list[EmergencyContact]:
    result = await db.execute(
        select(EmergencyContact).where(
            EmergencyContact.user_id == user_id,
            EmergencyContact.is_active == True,
        )
    )
    return list(result.scalars().all())
