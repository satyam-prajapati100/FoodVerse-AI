
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from models import MealAnalysis

router = APIRouter(prefix="/database", tags=["Database"])


class MealAnalysisCreate(BaseModel):
    dish_name: str = Field(min_length=1, max_length=255)
    image_path: str | None = Field(default=None, max_length=500)
    portion_weight_g: float | None = Field(default=None, gt=0)
    calories_kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    health_score: int | None = Field(default=None, ge=0, le=100)
    health_label: str | None = Field(default=None, max_length=50)


class MealAnalysisResponse(BaseModel):
    id: int
    dish_name: str
    image_path: str | None
    portion_weight_g: float | None
    calories_kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    health_score: int | None
    health_label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/analyses", response_model=MealAnalysisResponse)
def save_analysis(
    data: MealAnalysisCreate,
    db: Session = Depends(get_db),
):
    meal = MealAnalysis(**data.model_dump())

    try:
        db.add(meal)
        db.commit()
        db.refresh(meal)
        return meal
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the analysis to the database.",
        ) from exc


@router.get("/analyses", response_model=list[MealAnalysisResponse])
def get_analyses(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    try:
        return (
            db.query(MealAnalysis)
            .order_by(MealAnalysis.id.desc())
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve analyses from the database.",
        ) from exc
