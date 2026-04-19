from fastapi import APIRouter
from app.dependencies import DbDep, CurrentUserDep
from app.models.user import OnboardingRequest, OnboardingResponse, ProfileResponse, UpdateProfileRequest
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_profile(user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    profile = await svc.get_profile(user_id)
    if not profile:
        return ProfileResponse(user_id=user_id)

    health = profile.get("health") or {}
    aims = profile.get("aims") or {}
    return ProfileResponse(
        user_id=profile["user_id"],
        user_name=profile.get("user_name"),
        user_sex=profile.get("user_sex"),
        date_of_birth=profile.get("date_of_birth"),
        weight=health.get("weight"),
        height=health.get("height"),
        bmi=health.get("imt"),
        bmi_class=health.get("imt_str"),
        daily_cal=aims.get("daily_cal"),
        aim=aims.get("user_aim"),
        lang=profile.get("lang", "ru"),
    )


@router.post("/onboarding", response_model=OnboardingResponse)
async def onboarding(body: OnboardingRequest, user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    result = await svc.complete_onboarding(
        user_id=user_id,
        height=body.height, weight=body.weight,
        date_of_birth=body.date_of_birth,
        sex=body.sex, aim=body.aim,
    )
    return OnboardingResponse(**result)


@router.put("/me")
async def update_profile(body: UpdateProfileRequest, user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    if body.weight is not None or body.height is not None or body.aim is not None:
        return await svc.update_profile_data(
            user_id,
            weight=body.weight,
            height=body.height,
            aim=body.aim,
        )
    return {"message": "No changes"}
