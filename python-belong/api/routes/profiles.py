from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from profile.models import ProfileCreate, ProfileUpdate, ProfileResponse
from profile.repository import ProfileRepository

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate):
    existing = await ProfileRepository.get_profile(payload.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile for user {payload.user_id} already exists."
        )
    return await ProfileRepository.create_profile(payload)

@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: UUID):
    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found."
        )
    return profile

@router.patch("/{user_id}", response_model=ProfileResponse)
async def update_profile(user_id: UUID, payload: ProfileUpdate):
    profile = await ProfileRepository.update_profile(user_id, payload)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found."
        )
    return profile
