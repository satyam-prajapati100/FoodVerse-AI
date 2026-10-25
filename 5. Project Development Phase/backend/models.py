
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
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
