
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class MealAnalysis(Base):
    __tablename__ = "meal_analyses"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    image_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    dish_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    portion_weight_g: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    calories_kcal: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    protein_g: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    carbs_g: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    fat_g: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    fiber_g: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    health_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    health_label: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )


class UserProfileRecord(Base):
    """Persisted user profile for personalized meal planning."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)

    activity_level: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    goal: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    dietary_preference: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    allergies: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    dietary_restrictions: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    disliked_foods: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    preferred_cuisine: Mapped[str] = mapped_column(
        String(60), nullable=False, default="Any"
    )
    meals_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
