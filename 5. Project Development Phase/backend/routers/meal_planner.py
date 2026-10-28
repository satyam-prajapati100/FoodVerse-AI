
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from models import UserProfileRecord
from services.meal_recommendation import (
    calculate_targets,
    filter_meals,
    scale_meal_portion,
)

router = APIRouter(
    prefix="/meal-planner",
    tags=["Personalized Meal Planner"],
)


class UserProfile(BaseModel):
    """Validated user information for personalized meal planning."""
    age: int = Field(ge=18, le=100)
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=25, le=300)

    activity_level: Literal[
        "sedentary", "light", "moderate", "active", "very_active"
    ]
    goal: Literal["lose_weight", "maintain_weight", "gain_weight"]
    dietary_preference: Literal[
        "vegetarian", "vegan", "non_vegetarian", "eggetarian"
    ]

    allergies: list[str] = Field(default_factory=list, max_length=50)
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=50)
    disliked_foods: list[str] = Field(default_factory=list, max_length=50)

    preferred_cuisine: str = Field(default="Any", min_length=1, max_length=60)
    meals_per_day: int = Field(default=3, ge=1, le=8)

    @field_validator("allergies", "dietary_restrictions", "disliked_foods")
    @classmethod
    def clean_food_lists(cls, values: list[str]) -> list[str]:
        cleaned = []

        for value in values:
            item = value.strip()

            if not item:
                raise ValueError("Food preference entries cannot be empty.")

            if len(item) > 100:
                raise ValueError(
                    "Food preference entries must be 100 characters or fewer."
                )

            cleaned.append(item)

        return list(dict.fromkeys(cleaned))

    @field_validator("preferred_cuisine")
    @classmethod
    def clean_cuisine(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Preferred cuisine cannot be empty.")

        return value

    @model_validator(mode="after")
    def validate_profile_consistency(self):
        # Dietary restrictions and allergies are stored separately.
        return self


class UserProfileResponse(BaseModel):
    success: bool
    message: str
    profile_id: int
    profile: UserProfile


def profile_to_dict(record: UserProfileRecord) -> dict:
    """Convert a database record into the validated profile structure."""

    return {
        "age": record.age,
        "height_cm": record.height_cm,
        "weight_kg": record.weight_kg,
        "activity_level": record.activity_level,
        "goal": record.goal,
        "dietary_preference": record.dietary_preference,
        "allergies": record.allergies or [],
        "dietary_restrictions": record.dietary_restrictions or [],
        "disliked_foods": record.disliked_foods or [],
        "preferred_cuisine": record.preferred_cuisine,
        "meals_per_day": record.meals_per_day,
    }


@router.post("/profile", response_model=UserProfileResponse)
def process_user_profile(
    profile: UserProfile,
    db: Session = Depends(get_db),
):
    """Validate a profile and save it to MySQL."""

    record = UserProfileRecord(**profile.model_dump())

    try:
        db.add(record)
        db.commit()
        db.refresh(record)

        return UserProfileResponse(
            success=True,
            message="User profile validated and saved successfully.",
            profile_id=record.id,
            profile=profile,
        )

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the user profile to the database.",
        ) from exc


@router.get("/profile/{profile_id}", response_model=UserProfileResponse)
def get_user_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve a saved profile by its database ID."""

    record = db.get(UserProfileRecord, profile_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        )

    profile = UserProfile.model_validate(profile_to_dict(record))

    return UserProfileResponse(
        success=True,
        message="User profile retrieved successfully.",
        profile_id=record.id,
        profile=profile,
    )




def choose_meal(profile: dict, meal_type: str, used_ids: set[str]):
    """Choose a compatible meal, preferring meals not already selected."""
    candidates = filter_meals(profile, meal_type)
    unused = [meal for meal in candidates if meal["id"] not in used_ids]
    options = unused or candidates

    if not options:
        return None

    return options[0]


@router.post("/daily/{profile_id}")
def generate_daily_plan(
    profile_id: int,
    db: Session = Depends(get_db),
):
    """Generate a daily plan with approximate portion scaling."""

    record = db.get(UserProfileRecord, profile_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        )

    profile = profile_to_dict(record)
    targets = calculate_targets(profile)
    calorie_target = targets["estimated_daily_calories_kcal"]

    meal_types = ["breakfast", "lunch", "dinner"]

    if profile["meals_per_day"] >= 4:
        meal_types.append("snack")

    # Select compatible meals first.
    used_ids: set[str] = set()
    base_meals = []

    for meal_type in meal_types:
        meal = choose_meal(profile, meal_type, used_ids)

        if meal is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No compatible {meal_type} found. "
                    "Review the dietary preferences and meal catalog."
                ),
            )

        used_ids.add(meal["id"])
        base_meals.append(meal)

    # Estimate a common portion multiplier that approaches the
    # daily calorie target. Keep portions within a demonstration range.
    base_calories = sum(meal["calories"] for meal in base_meals)

    if base_calories <= 0:
        raise HTTPException(
            status_code=500,
            detail="Meal catalog contains invalid calorie values.",
        )

    multiplier = max(
        0.5,
        min(2.5, calorie_target / base_calories),
    )

    selected_meals = [
        scale_meal_portion(meal, multiplier)
        for meal in base_meals
    ]

    total = {
        "calories_kcal": sum(meal["calories"] for meal in selected_meals),
        "protein_g": sum(meal["protein"] for meal in selected_meals),
        "carbs_g": sum(meal["carbs"] for meal in selected_meals),
        "fat_g": sum(meal["fat"] for meal in selected_meals),
    }

    calorie_difference = total["calories_kcal"] - calorie_target

    return {
        "success": True,
        "profile_id": record.id,
        "goal": profile["goal"],
        "targets": targets,
        "meals": selected_meals,
        "nutrition_summary": total,
        "calorie_comparison": {
            "target_kcal": calorie_target,
            "planned_kcal": total["calories_kcal"],
            "difference_kcal": calorie_difference,
            "within_10_percent": (
                abs(calorie_difference) <= calorie_target * 0.10
            ),
        },
        "notes": [
            "Nutrition values are illustrative estimates from a small demonstration catalog.",
            "A common portion multiplier is used; this does not guarantee balanced nutrition.",
            "Daily calorie targets are educational estimates, not medical advice.",
            "Ingredient matching cannot guarantee allergen safety.",
        ],
    }
